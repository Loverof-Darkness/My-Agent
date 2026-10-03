
import os
import re
import json
import shlex
import subprocess
import fnmatch
from pathlib import Path
from typing import Any, Callable

ROOT = Path("/content/drive/MyDrive/MyAgent-Coder")
WORKSPACE = ROOT / "projects" / "workspace"
MEMORY_DIR = ROOT / "memory"
SKILLS_ROOT = ROOT / "agent" / "skills" / "Agent_Skills"

WORKSPACE.mkdir(parents=True, exist_ok=True)
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# SAFE PATH
# ============================================================

def safe_path(relative_path=""):
    p = (WORKSPACE / relative_path).resolve()
    if p != WORKSPACE.resolve() and WORKSPACE.resolve() not in p.parents:
        raise ValueError(f"Unsafe workspace path: {relative_path}")
    return p


# ============================================================
# FILESYSTEM TOOLS
# ============================================================

def list_files(relative_path=""):
    path = safe_path(relative_path)
    if not path.exists():
        return {"success": False, "error": f"Not found: {relative_path}"}

    results = []
    for item in sorted(path.iterdir(), key=lambda x: x.name.lower()):
        results.append({
            "name": item.name,
            "type": "directory" if item.is_dir() else "file",
            "size": item.stat().st_size if item.is_file() else None,
        })
    return results


def read_file(relative_path):
    path = safe_path(relative_path)
    if not path.is_file():
        raise FileNotFoundError(relative_path)
    return path.read_text(encoding="utf-8")


def write_file(relative_path, content):
    path = safe_path(relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {
        "path": str(path.relative_to(WORKSPACE)),
        "bytes": path.stat().st_size,
    }


def search_files(pattern="*"):
    results = []
    for path in WORKSPACE.rglob("*"):
        if path.is_file() and fnmatch.fnmatch(path.name, pattern):
            results.append(str(path.relative_to(WORKSPACE)))
    return sorted(results)


def patch_file(relative_path, old_text, new_text, count=1):
    path = safe_path(relative_path)
    text = path.read_text(encoding="utf-8")

    occurrences = text.count(old_text)

    if occurrences == 0:
        return {
            "success": False,
            "error": "old_text not found",
        }

    if count > occurrences:
        count = occurrences

    updated = text.replace(old_text, new_text, count)
    path.write_text(updated, encoding="utf-8")

    return {
        "success": True,
        "path": str(path.relative_to(WORKSPACE)),
        "replacements": count,
    }


# ============================================================
# CONTROLLED COMMAND EXECUTOR
# ============================================================

BLOCKED_PATTERNS = [
    "rm -rf",
    "sudo ",
    "mkfs",
    "dd if=",
    "shutdown",
    "reboot",
    "poweroff",
    "chmod 777",
    "chown ",
    "mount ",
    "umount ",
    "kill -9",
    "&&",
    "||",
    ";",
    "|",
    ">",
    "<",
    "`",
    "$(",
]

def run_command(command, timeout=120):
    command = str(command)

    lowered = command.lower()

    for bad in BLOCKED_PATTERNS:
        if bad in lowered:
            return {
                "success": False,
                "blocked": True,
                "error": f"Blocked command pattern: {bad}",
            }

    try:
        args = shlex.split(command)
    except ValueError as e:
        return {
            "success": False,
            "error": f"Invalid command syntax: {e}",
        }

    if not args:
        return {
            "success": False,
            "error": "Empty command",
        }

    try:
        p = subprocess.run(
            args,
            cwd=str(WORKSPACE),
            shell=False,
            capture_output=True,
            text=True,
            timeout=int(timeout),
        )

        return {
            "success": p.returncode == 0,
            "returncode": p.returncode,
            "stdout": p.stdout,
            "stderr": p.stderr,
            "command": command,
        }

    except subprocess.TimeoutExpired as e:
        return {
            "success": False,
            "timeout": True,
            "error": f"Command timed out after {timeout}s",
            "stdout": e.stdout or "",
            "stderr": e.stderr or "",
        }


# ============================================================
# GIT TOOLS
# ============================================================

def _git(args):
    return run_command("git " + " ".join(shlex.quote(str(x)) for x in args))


def git_status():
    return _git(["status", "--short", "--branch"])


def git_diff():
    return _git(["diff"])


def git_log(limit=10):
    return _git(["log", "--oneline", f"-{int(limit)}"])


def git_branch():
    return _git(["branch", "--show-current"])


def git_remote():
    return _git(["remote", "-v"])


def git_add(paths=None):
    if paths is None:
        paths = ["."]

    if isinstance(paths, str):
        paths = [paths]

    return _git(["add", *paths])


def git_commit(message):
    return _git(["commit", "-m", message])


# ============================================================
# SKILLS
# ============================================================

def _skill_files():
    if not SKILLS_ROOT.exists():
        return []

    return list(SKILLS_ROOT.rglob("SKILL.md"))


def list_skills():
    result = []

    for p in _skill_files():
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        name = p.parent.name

        m = re.search(
            r"^name:\s*(.+)$",
            text,
            re.MULTILINE,
        )

        if m:
            name = m.group(1).strip()

        result.append({
            "name": name,
            "path": str(p),
        })

    return sorted(result, key=lambda x: x["name"].lower())


def _find_skill(name):
    name = str(name).strip()

    for p in _skill_files():
        if p.parent.name == name:
            return p

        try:
            text = p.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except Exception:
            continue

        if re.search(
            rf"^name:\s*{re.escape(name)}\s*$",
            text,
            re.MULTILINE,
        ):
            return p

    return None


def load_skill(skill_name):
    p = _find_skill(skill_name)

    if p is None:
        return {
            "success": False,
            "error": f"Skill not found: {skill_name}",
        }

    return {
        "success": True,
        "name": str(skill_name),
        "path": str(p),
        "content": p.read_text(
            encoding="utf-8",
            errors="ignore",
        ),
    }


def search_agent_skills(query):
    query = str(query).lower()
    results = []

    for p in _skill_files():
        try:
            text = p.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except Exception:
            continue

        score = sum(
            text.lower().count(term)
            for term in query.split()
            if term
        )

        if score:
            results.append({
                "name": p.parent.name,
                "path": str(p),
                "score": score,
            })

    return sorted(
        results,
        key=lambda x: x["score"],
        reverse=True,
    )[:10]


def load_agent_skill(skill_name):
    return load_skill(skill_name)


# ============================================================
# PERSISTENT MEMORY
# ============================================================

MEMORY_FILE = MEMORY_DIR / "persistent_memory.json"

def remember(key, value):
    data = {}

    if MEMORY_FILE.exists():
        try:
            data = json.loads(
                MEMORY_FILE.read_text(encoding="utf-8")
            )
        except Exception:
            data = {}

    data[key] = value

    MEMORY_FILE.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )

    return {
        "success": True,
        "key": key,
    }


# ============================================================
# TOOL REGISTRY
# ============================================================

def _register(name, description, parameters, function):
    return {
        "name": name,
        "description": description,
        "parameters": parameters,
        "function": function,
    }


TOOL_REGISTRY_ACTIVE = {
    "list_files": _register(
        "list_files",
        "List files and directories inside the agent workspace.",
        {
            "type": "object",
            "properties": {
                "relative_path": {"type": "string"}
            },
        },
        list_files,
    ),

    "read_file": _register(
        "read_file",
        "Read a UTF-8 text file inside the agent workspace.",
        {
            "type": "object",
            "properties": {
                "relative_path": {"type": "string"}
            },
            "required": ["relative_path"],
        },
        read_file,
    ),

    "write_file": _register(
        "write_file",
        "Create or overwrite a UTF-8 text file inside the agent workspace.",
        {
            "type": "object",
            "properties": {
                "relative_path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["relative_path", "content"],
        },
        write_file,
    ),

    "search_files": _register(
        "search_files",
        "Search for files matching a filename pattern.",
        {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"}
            },
        },
        search_files,
    ),

    "patch_file": _register(
        "patch_file",
        "Replace existing text in a workspace file.",
        {
            "type": "object",
            "properties": {
                "relative_path": {"type": "string"},
                "old_text": {"type": "string"},
                "new_text": {"type": "string"},
                "count": {"type": "integer"},
            },
            "required": [
                "relative_path",
                "old_text",
                "new_text",
            ],
        },
        patch_file,
    ),

    "run_command": _register(
        "run_command",
        "Run a controlled command from the workspace.",
        {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "timeout": {"type": "integer"},
            },
            "required": ["command"],
        },
        run_command,
    ),

    "git_status": _register(
        "git_status",
        "Show Git working tree status.",
        {"type": "object", "properties": {}},
        git_status,
    ),

    "git_diff": _register(
        "git_diff",
        "Show Git diff.",
        {"type": "object", "properties": {}},
        git_diff,
    ),

    "git_log": _register(
        "git_log",
        "Show recent Git commits.",
        {
            "type": "object",
            "properties": {
                "limit": {"type": "integer"}
            },
        },
        git_log,
    ),

    "git_branch": _register(
        "git_branch",
        "Show current Git branch.",
        {"type": "object", "properties": {}},
        git_branch,
    ),

    "git_remote": _register(
        "git_remote",
        "Show configured Git remotes.",
        {"type": "object", "properties": {}},
        git_remote,
    ),

    "git_add": _register(
        "git_add",
        "Stage files for Git commit.",
        {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                }
            },
        },
        git_add,
    ),

    "git_commit": _register(
        "git_commit",
        "Create a Git commit.",
        {
            "type": "object",
            "properties": {
                "message": {"type": "string"}
            },
            "required": ["message"],
        },
        git_commit,
    ),

    "list_skills": _register(
        "list_skills",
        "List available Agent_Skills skills.",
        {"type": "object", "properties": {}},
        list_skills,
    ),

    "load_skill": _register(
        "load_skill",
        "Load a complete SKILL.md.",
        {
            "type": "object",
            "properties": {
                "skill_name": {"type": "string"}
            },
            "required": ["skill_name"],
        },
        load_skill,
    ),

    "remember": _register(
        "remember",
        "Persist information in agent memory.",
        {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "value": {},
            },
            "required": ["key", "value"],
        },
        remember,
    ),

    "search_agent_skills": _register(
        "search_agent_skills",
        "Search Agent_Skills for relevant skills.",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"],
        },
        search_agent_skills,
    ),

    "load_agent_skill": _register(
        "load_agent_skill",
        "Load an Agent_Skills SKILL.md.",
        {
            "type": "object",
            "properties": {
                "skill_name": {"type": "string"}
            },
            "required": ["skill_name"],
        },
        load_agent_skill,
    ),
}


# ============================================================
# TOOL EXECUTION
# ============================================================


def _normalize_tool_result(result):
    """
    Normalize every tool result to a predictable evidence format.

    Accepted:
      - {"success": True, ...}
      - {"success": False, ...}
      - None
      - strings
      - arbitrary objects

    The strict controller must never confuse a missing/None result
    with a successful mutation.
    """

    if isinstance(result, dict):
        normalized = dict(result)

        if "success" in normalized:
            normalized["success"] = bool(normalized["success"])
            return normalized

        # Some tools may return {"error": ...} without success.
        if "error" in normalized:
            normalized["success"] = False
            return normalized

        # Dict without explicit status means the tool returned data.
        normalized["success"] = True
        return normalized

    if result is None:
        return {
            "success": False,
            "result": None,
            "error": "Tool returned None; operation success is unproven.",
        }

    return {
        "success": True,
        "result": result,
    }


def _execute_registered_tool(tool_name, arguments):
    """
    Execute one registered tool and normalize its result.

    This is the sole boundary between the agent controller and
    actual tools.
    """

    if tool_name not in TOOL_REGISTRY_ACTIVE:
        return {
            "success": False,
            "error": f"Unknown tool: {tool_name}",
        }

    spec = TOOL_REGISTRY_ACTIVE[tool_name]

    try:
        # Registry entries may be:
        #   {"function": fn}
        #   {"fn": fn}
        #   {"callable": fn}
        # or a callable directly.

        if isinstance(spec, dict):
            fn = (
                spec.get("function")
                or spec.get("fn")
                or spec.get("callable")
            )
        else:
            fn = spec

        if not callable(fn):
            return {
                "success": False,
                "error": (
                    f"Tool '{tool_name}' has no callable implementation."
                ),
            }

        if not isinstance(arguments, dict):
            return {
                "success": False,
                "error": "Tool arguments must be a JSON object.",
            }

        result = fn(**arguments)

        return _normalize_tool_result(result)

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "exception": type(e).__name__,
        }


def _qwen_generate(system_prompt, conversation, max_tokens=768):
    messages = []

    if system_prompt:
        messages.append({
            "role": "system",
            "content": str(system_prompt),
        })

    for msg in conversation:
        role = msg.get("role", "user")

        if role not in ("system", "user", "assistant"):
            role = "user"

        messages.append({
            "role": role,
            "content": str(msg.get("content", "")),
        })

    result = QWEN.create_chat_completion(
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.0,
        top_p=1.0,
        stream=False,
    )

    return result["choices"][0]["message"]["content"]


# ============================================================
# JSON TOOL PARSER
# ============================================================

def _extract_json_tool_call(text):
    text = str(text).strip()

    candidates = [text]

    fenced = re.findall(
        r"```(?:json)?\s*(.*?)\s*```",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    candidates.extend(fenced)

    for candidate in candidates:
        try:
            obj = json.loads(candidate)

            if (
                isinstance(obj, dict)
                and isinstance(obj.get("tool"), str)
                and isinstance(obj.get("arguments"), dict)
            ):
                return obj

        except Exception:
            pass

    # Search for an embedded JSON object.
    match = re.search(
        r'\{\s*"tool"\s*:\s*"[^"]+"\s*,\s*"arguments"\s*:\s*\{.*?\}\s*\}',
        text,
        flags=re.DOTALL,
    )

    if match:
        try:
            obj = json.loads(match.group(0))

            if (
                isinstance(obj, dict)
                and isinstance(obj.get("tool"), str)
                and isinstance(obj.get("arguments"), dict)
            ):
                return obj

        except Exception:
            pass

    return None


# ============================================================
# SKILL ROUTING
# ============================================================

def select_skill(task):
    task = str(task).lower()

    rules = [
        (
            "investigate",
            [
                "debug",
                "broken",
                "crash",
                "error",
                "why",
                "root cause",
                "investigate",
                "fix bug",
            ],
        ),
        (
            "review",
            [
                "security",
                "review",
                "audit",
                "vulnerability",
            ],
        ),
        (
            "qa",
            [
                "test",
                "testing",
                "pytest",
                "verify",
                "quality",
            ],
        ),
        (
            "plan-eng-review",
            [
                "architecture",
                "design",
                "plan",
                "refactor",
            ],
        ),
        (
            "benchmark",
            [
                "performance",
                "benchmark",
                "optimize",
                "slow",
            ],
        ),
    ]

    candidates = []

    for name, keywords in rules:
        score = sum(1 for k in keywords if k in task)

        if score:
            candidates.append({
                "name": name,
                "score": score,
                "reason": "Matched task keywords.",
            })

    candidates.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    if candidates:
        selected = candidates[0]["name"]
    else:
        selected = "investigate"

    return {
        "selected": {
            "skill": selected,
            "reason": "Highest-ranked applicable skill.",
        },
        "candidates": candidates,
    }


def resolve_selected_skill(selection):
    name = selection["selected"]["skill"]

    p = _find_skill(name)

    if p is None:
        return {
            "name": name,
            "path": None,
            "content": "",
        }

    return {
        "name": name,
        "path": str(p),
        "content": p.read_text(
            encoding="utf-8",
            errors="ignore",
        ),
    }


# ============================================================
# PROGRESSIVE SKILL CONTEXT
# ============================================================

def build_compact_skill_context(
    skill_name,
    task,
    max_chars=12000,
):
    skill = load_skill(skill_name)

    if not skill.get("success"):
        return ""

    text = skill["content"]

    if len(text) <= max_chars:
        return text

    task_terms = [
        x.lower()
        for x in re.findall(r"[A-Za-z0-9_-]+", str(task))
        if len(x) > 3
    ]

    sections = re.split(
        r"(?=^#{1,4}\s+)",
        text,
        flags=re.MULTILINE,
    )

    scored = []

    for section in sections:
        lower = section.lower()

        score = 0

        if any(
            term in lower
            for term in [
                "must",
                "required",
                "workflow",
                "safety",
                "verification",
                "root cause",
                "evidence",
            ]
        ):
            score += 3

        score += sum(
            1 for term in task_terms
            if term in lower
        )

        scored.append((score, section))

    scored.sort(
        key=lambda x: x[0],
        reverse=True,
    )

    output = []

    for _, section in scored:
        candidate = "".join(output) + section

        if len(candidate) > max_chars:
            break

        output.append(section)

    result = "".join(output)

    if not result:
        result = text[:max_chars]

    return result[:max_chars]


# ============================================================
# SYSTEM PROMPT
# ============================================================

def _tool_descriptions():
    return [
        {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["parameters"],
        }
        for t in TOOL_REGISTRY_ACTIVE.values()
    ]


def build_progressive_system_prompt(
    task,
    skill_name,
    compact_skill,
):
    tools = json.dumps(
        _tool_descriptions(),
        indent=2,
        ensure_ascii=False,
    )

    return f"""
You are MyAgent-Coder, a local coding agent powered by
Qwen2.5-Coder-14B.

You operate only inside the assigned workspace.

WORKSPACE:
{WORKSPACE}

ACTIVE SKILL:
{skill_name}

SKILL GUIDANCE:
{compact_skill}

AVAILABLE TOOLS:
{tools}

TOOL FORMAT:

When you need a tool, output ONLY:

{{
  "tool": "tool_name",
  "arguments": {{
    "argument": "value"
  }}
}}

Rules:

- Never invent tool names.
- Never invent tool arguments.
- Inspect files before modifying them.
- Use workspace-relative paths.
- Never access files outside the workspace.
- Never claim a tool was used unless a real tool result exists.
- Never claim a file changed unless a write/patch tool succeeded.
- Use actual tool results as evidence.
- Verify important changes with the appropriate command/test.
- If no modification is required, say so.
- Do not fabricate test results.
- Follow the active Agent_Skills guidance.
"""


# ============================================================
# STRICT AGENT
# ============================================================

def coder_agent_skill_aware_progressive(
    task,
    max_steps=20,
    max_tokens=768,
    skill_context_chars=12000,
    verbose=True,
):
    selection = select_skill(task)
    skill = resolve_selected_skill(selection)
    skill_name = skill["name"]

    compact_skill = build_compact_skill_context(
        skill_name,
        task,
        skill_context_chars,
    )

    system_prompt = build_progressive_system_prompt(
        task,
        skill_name,
        compact_skill,
    )

    conversation = [
        {
            "role": "user",
            "content": str(task),
        }
    ]

    tool_history = []

    for step in range(1, max_steps + 1):

        if verbose:
            print(f"\nSTEP {step}/{max_steps}")
            print("-" * 70)

        response = _qwen_generate(
            system_prompt,
            conversation,
            max_tokens=max_tokens,
        ).strip()

        tool_call = _extract_json_tool_call(response)

        if tool_call is None:
            conversation.append({
                "role": "assistant",
                "content": response,
            })

            return {
                "status": "completed",
                "answer": response,
                "skill": skill_name,
                "steps": step,
                "tool_history": tool_history,
                "conversation": conversation,
            }

        tool_name = tool_call["tool"]
        arguments = tool_call["arguments"]

        if verbose:
            print("TOOL:", tool_name)
            print(
                "ARGS:",
                json.dumps(
                    arguments,
                    ensure_ascii=False,
                ),
            )

        conversation.append({
            "role": "assistant",
            "content": response,
        })

        result = _execute_registered_tool(
            tool_name,
            arguments,
        )

        tool_history.append({
            "step": step,
            "tool": tool_name,
            "arguments": arguments,
            "result": result,
        })

        conversation.append({
            "role": "user",
            "content": (
                "TOOL RESULT\n"
                f"Tool: {tool_name}\n"
                "Result:\n"
                + json.dumps(
                    result,
                    ensure_ascii=False,
                    default=str,
                )
                + "\n\n"
                "Continue using only actual evidence from "
                "the tool result."
            ),
        })

    return {
        "status": "max_steps_reached",
        "answer": "Maximum agent steps reached.",
        "skill": skill_name,
        "steps": max_steps,
        "tool_history": tool_history,
        "conversation": conversation,
    }


coder_agent = coder_agent_skill_aware_progressive


# ============================================================
# PERSISTENT SESSION WRAPPER
# ============================================================

SESSION_FILE = MEMORY_DIR / "agent_sessions.json"

# Preserve the actual progressive implementation.
_coder_agent_core = coder_agent_skill_aware_progressive


def coder_agent_persistent(task, **kwargs):
    history = []

    if SESSION_FILE.exists():
        try:
            history = json.loads(
                SESSION_FILE.read_text(
                    encoding="utf-8"
                )
            )
        except Exception:
            history = []

    # IMPORTANT:
    # Call the core agent, NOT coder_agent.
    # coder_agent is the public persistent wrapper.
    result = _coder_agent_core(task, **kwargs)

    history.append({
        "task": str(task),
        "status": result.get("status"),
        "skill": result.get("skill"),
        "steps": result.get("steps"),
        "answer": result.get("answer"),
        "tools": [
            {
                "tool": x["tool"],
                "arguments": x["arguments"],
            }
            for x in result.get("tool_history", [])
        ],
    })

    history = history[-20:]

    SESSION_FILE.write_text(
        json.dumps(
            history,
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )

    return result


# Public canonical agent.
coder_agent = coder_agent_persistent


# ============================================================
# MYAGENT-CODER STRICT EVIDENCE-GATED STATE MACHINE
# ============================================================

def _strict_task_needs_inspection(task):
    """Determine whether the task concerns repository/workspace state."""
    t = str(task).lower()

    indicators = [
        "file", "files", "code", "repository", "repo",
        "project", "workspace", "function", "class",
        "bug", "error", "crash", "fix", "modify",
        "change", "edit", "implement", "refactor",
        "test", "tests", "run", "verify", "check",
        "inspect", "review", "debug", "github", "git"
    ]

    return any(x in t for x in indicators)


def _strict_task_requests_verification(task):
    """Verification must be evidence-producing, not merely claimed."""
    t = str(task).lower()

    indicators = [
        "verify", "verified", "test", "tests", "testing",
        "run", "execute", "confirm", "prove", "validate",
        "check that", "make sure", "ensure"
    ]

    return any(x in t for x in indicators)


def _strict_tool_is_inspection(tool_name):
    return tool_name in {
        "read_file",
        "search_files",
        "list_files",
        "git_status",
        "git_diff",
        "git_log",
        "git_branch",
        "git_remote",
        "list_skills",
        "search_agent_skills",
        "load_skill",
        "load_agent_skill",
    }


def _strict_tool_is_modification(tool_name):
    return tool_name in {
        "write_file",
        "patch_file",
        "git_add",
        "git_commit",
    }


def _strict_tool_is_verification(tool_name):
    return tool_name in {
        "run_command",
        "read_file",
        "git_diff",
        "git_status",
    }


def _strict_extract_decision(text):
    """
    Accept ONLY an exact JSON decision object.
    No prose-based modification decisions are accepted.
    """
    text = str(text).strip()

    candidates = []

    # Entire response
    candidates.append(text)

    # JSON objects embedded in response
    for m in re.finditer(r'\{[^{}]*\}', text, re.DOTALL):
        candidates.append(m.group(0))

    for candidate in candidates:
        try:
            obj = json.loads(candidate)
        except Exception:
            continue

        if (
            isinstance(obj, dict)
            and obj.get("decision") in {"modify", "no_change"}
        ):
            return obj

    return None


def _strict_extract_tool(text):
    """
    Reuse the normal tool-call parser, but reject malformed calls.
    """
    try:
        result = _extract_json_tool_call(text)
    except Exception:
        return None

    if not isinstance(result, dict):
        return None

    tool = result.get("tool")
    args = result.get("arguments")

    if not isinstance(tool, str):
        return None

    if not isinstance(args, dict):
        return None

    if tool not in TOOL_REGISTRY_ACTIVE:
        return None

    return {
        "tool": tool,
        "arguments": args,
    }


def _strict_generate(system_prompt, conversation, max_tokens=512):
    response = _qwen_generate(
        system_prompt=system_prompt,
        conversation=conversation,
        max_tokens=max_tokens,
    )

    if response is None:
        return ""

    return str(response).strip()


def coder_agent_strict(
    task,
    max_steps=12,
    max_tokens=512,
    verbose=True,
):
    """
    Evidence-gated coding agent.

    State machine:

        INSPECT
           ↓
        DECIDE
        ↙    ↘
    no_change MODIFY
       ↓       ↓
      VERIFY ←─┘
       ↓
      FINAL

    A claimed modification/test is not accepted unless the
    corresponding real tool was executed.
    """

    task = str(task).strip()

    if not task:
        return {
            "status": "failed",
            "answer": "Task is empty.",
            "skill": None,
            "steps": 0,
            "tool_history": [],
            "state": "FINAL",
        }

    # --------------------------------------------------------
    # Skill routing
    # --------------------------------------------------------

    skill_name = None
    compact_skill = ""

    try:
        selection = select_skill(task)

        if isinstance(selection, dict):
            selected = selection.get("selected")

            if isinstance(selected, dict):
                skill_name = selected.get("skill")
            elif isinstance(selected, str):
                skill_name = selected

        if not skill_name:
            skill_name = "investigate"

        try:
            compact_skill = build_compact_skill_context(
                skill_name=skill_name,
                task=task,
                max_chars=10000,
            )
        except Exception:
            compact_skill = ""

    except Exception:
        skill_name = "investigate"
        compact_skill = ""

    # --------------------------------------------------------
    # Controller state
    # --------------------------------------------------------

    needs_inspection = _strict_task_needs_inspection(task)
    needs_verification = _strict_task_requests_verification(task)

    state = "INSPECT" if needs_inspection else "DECIDE"

    inspected = False
    decision = None
    modified = False
    verified = False

    tool_history = []
    conversation = [
        {
            "role": "user",
            "content": task,
        }
    ]

    started = time.time()

    base_system = f"""
You are MyAgent-Coder, a real repository coding agent.

You MUST operate using actual registered tools.
Never claim that a tool was used unless its tool result appears in the conversation.

Selected skill:
{skill_name}

Relevant skill guidance:
{compact_skill}

TASK:
{task}

STRICT EVIDENCE RULES:
- Never invent file contents.
- Never claim a modification without an actual write_file or patch_file result.
- Never claim a test was executed without an actual run_command result.
- Never claim verification from intention alone.
- Use only evidence returned by tools.
- Keep tool arguments exact and valid.

STATE MACHINE:
INSPECT -> DECIDE -> MODIFY -> VERIFY -> FINAL

The controller may reject a response that violates the current state.
"""

    if verbose:
        print("=" * 70)
        print("STRICT AGENT")
        print("=" * 70)
        print(f"Skill : {skill_name}")
        print(f"State : {state}")
        print()

    # --------------------------------------------------------
    # Helper: execute actual tool
    # --------------------------------------------------------

    def execute_tool(tool_call, current_state):
        nonlocal inspected, modified, verified

        tool_name = tool_call["tool"]
        arguments = tool_call["arguments"]

        # State-level restrictions
        if current_state == "INSPECT":
            if not _strict_tool_is_inspection(tool_name):
                return {
                    "success": False,
                    "error": (
                        f"Tool '{tool_name}' is not permitted during INSPECT. "
                        "Use a read/search/status tool first."
                    ),
                }

        elif current_state == "MODIFY":
            if not _strict_tool_is_modification(tool_name):
                return {
                    "success": False,
                    "error": (
                        f"Tool '{tool_name}' is not permitted during MODIFY. "
                        "Use write_file or patch_file."
                    ),
                }

        elif current_state == "VERIFY":
            if not _strict_tool_is_verification(tool_name):
                return {
                    "success": False,
                    "error": (
                        f"Tool '{tool_name}' is not permitted during VERIFY. "
                        "Use run_command/read_file/git_diff/git_status."
                    ),
                }

        try:
            result = _execute_registered_tool(tool_name, arguments)
        except Exception as e:
            result = {
                "success": False,
                "error": str(e),
                "exception": type(e).__name__,
            }

        tool_history.append({
            "step": len(tool_history) + 1,
            "state": current_state,
            "tool": tool_name,
            "arguments": arguments,
            "result": result,
        })

        if result.get("success") is True:
            if current_state == "INSPECT":
                inspected = True

            if current_state == "MODIFY":
                modified = True

            if current_state == "VERIFY":
                verified = True

        return result

    # --------------------------------------------------------
    # Main state machine
    # --------------------------------------------------------

    for step in range(1, max_steps + 1):

        if verbose:
            print(f"STEP {step}/{max_steps}")
            print("-" * 70)
            print(f"STATE: {state}")

        # ====================================================
        # INSPECT
        # ====================================================

        if state == "INSPECT":

            prompt = base_system + """

CURRENT STATE: INSPECT

You MUST inspect the relevant repository/workspace state before making
any decision about modification.

Return exactly ONE JSON tool call and nothing else:

{
  "tool": "read_file",
  "arguments": {
    "relative_path": "..."
  }
}

OR another valid inspection tool from the registered tools.

Do NOT modify anything.
"""

            response = _strict_generate(
                prompt,
                conversation,
                max_tokens=max_tokens,
            )

            tool_call = _strict_extract_tool(response)

            if not tool_call:
                conversation.append({
                    "role": "assistant",
                    "content": response,
                })
                conversation.append({
                    "role": "user",
                    "content": (
                        "STATE VIOLATION. INSPECT requires one actual "
                        "inspection tool call. Return only the JSON tool call."
                    ),
                })
                continue

            conversation.append({
                "role": "assistant",
                "content": response,
            })

            result = execute_tool(tool_call, "INSPECT")

            conversation.append({
                "role": "user",
                "content": (
                    "ACTUAL TOOL RESULT\n"
                    f"Tool: {tool_call['tool']}\n"
                    f"Result:\n"
                    f"{json.dumps(result, ensure_ascii=False, default=str)}\n\n"
                    "Inspection evidence is now available."
                ),
            })

            if result.get("success") is True:
                state = "DECIDE"

            continue

        # ====================================================
        # DECIDE
        # ====================================================

        if state == "DECIDE":

            prompt = base_system + """

CURRENT STATE: DECIDE

Inspection evidence has been collected.

Decide whether the requested task requires a repository/workspace
modification.

You MUST return EXACTLY one JSON object:

{"decision":"modify"}

or:

{"decision":"no_change"}

Do not include prose.
"""

            response = _strict_generate(
                prompt,
                conversation,
                max_tokens=128,
            )

            parsed = _strict_extract_decision(response)

            if parsed is None:
                conversation.append({
                    "role": "assistant",
                    "content": response,
                })
                conversation.append({
                    "role": "user",
                    "content": (
                        "STATE VIOLATION. DECIDE requires exactly "
                        '{"decision":"modify"} or '
                        '{"decision":"no_change"}.'
                    ),
                })
                continue

            decision = parsed["decision"]

            conversation.append({
                "role": "assistant",
                "content": json.dumps(parsed),
            })

            if decision == "modify":
                state = "MODIFY"
            else:
                state = "VERIFY" if needs_verification else "FINAL"

            continue

        # ====================================================
        # MODIFY
        # ====================================================

        if state == "MODIFY":

            prompt = base_system + """

CURRENT STATE: MODIFY

The decision is MODIFY.

You MUST now perform the requested modification using an actual
write_file or patch_file tool.

Return exactly ONE JSON tool call.

Do not claim success in prose.
"""

            response = _strict_generate(
                prompt,
                conversation,
                max_tokens=max_tokens,
            )

            tool_call = _strict_extract_tool(response)

            if not tool_call or not _strict_tool_is_modification(
                tool_call["tool"]
            ):
                conversation.append({
                    "role": "assistant",
                    "content": response,
                })
                conversation.append({
                    "role": "user",
                    "content": (
                        "STATE VIOLATION. MODIFY requires an actual "
                        "write_file or patch_file tool call."
                    ),
                })
                continue

            conversation.append({
                "role": "assistant",
                "content": response,
            })

            result = execute_tool(tool_call, "MODIFY")

            conversation.append({
                "role": "user",
                "content": (
                    "ACTUAL MODIFICATION RESULT\n"
                    f"Tool: {tool_call['tool']}\n"
                    f"Result:\n"
                    f"{json.dumps(result, ensure_ascii=False, default=str)}"
                ),
            })

            if result.get("success") is True:
                state = "VERIFY"
            else:
                state = "FINAL"

            continue

        # ====================================================
        # VERIFY
        # ====================================================

        if state == "VERIFY":

            if not modified and not needs_verification:
                state = "FINAL"
                continue

            prompt = base_system + """

CURRENT STATE: VERIFY

Verification MUST produce actual evidence.

If a test or command is requested, use run_command.
If checking the changed file is appropriate, use read_file.
If repository state is relevant, use git_diff or git_status.

Return exactly ONE JSON tool call.
Do not merely state that verification passed.
"""

            response = _strict_generate(
                prompt,
                conversation,
                max_tokens=max_tokens,
            )

            tool_call = _strict_extract_tool(response)

            if not tool_call or not _strict_tool_is_verification(
                tool_call["tool"]
            ):
                conversation.append({
                    "role": "assistant",
                    "content": response,
                })
                conversation.append({
                    "role": "user",
                    "content": (
                        "STATE VIOLATION. VERIFY requires an actual "
                        "verification tool call."
                    ),
                })
                continue

            conversation.append({
                "role": "assistant",
                "content": response,
            })

            result = execute_tool(tool_call, "VERIFY")

            conversation.append({
                "role": "user",
                "content": (
                    "ACTUAL VERIFICATION RESULT\n"
                    f"Tool: {tool_call['tool']}\n"
                    f"Result:\n"
                    f"{json.dumps(result, ensure_ascii=False, default=str)}"
                ),
            })

            if result.get("success") is True:
                verified = True

            state = "FINAL"
            continue

        # ====================================================
        # FINAL
        # ====================================================

        if state == "FINAL":

            evidence = {
                "inspected": inspected,
                "decision": decision,
                "modified": modified,
                "verified": verified,
                "tools": len(tool_history),
            }

            prompt = base_system + f"""

CURRENT STATE: FINAL

Produce the final answer using ONLY actual evidence.

Controller evidence:
{json.dumps(evidence, indent=2)}

Rules:
- If modified=true, only say it was modified because a real
  modification tool succeeded.
- If verified=true, only say it was verified because a real
  verification tool succeeded.
- If no_change was selected, say no modification was required.
- Do not invent test results.
- Be concise.
"""

            response = _strict_generate(
                prompt,
                conversation,
                max_tokens=max_tokens,
            )

            conversation.append({
                "role": "assistant",
                "content": response,
            })

            elapsed = time.time() - started

            return {
                "status": "completed",
                "answer": response,
                "skill": skill_name,
                "steps": step,
                "state": "FINAL",
                "decision": decision,
                "inspected": inspected,
                "modified": modified,
                "verified": verified,
                "tool_history": tool_history,
                "elapsed_seconds": round(elapsed, 3),
                "conversation": conversation,
            }

    return {
        "status": "max_steps_reached",
        "answer": "Strict state machine reached maximum steps.",
        "skill": skill_name,
        "steps": max_steps,
        "state": state,
        "decision": decision,
        "inspected": inspected,
        "modified": modified,
        "verified": verified,
        "tool_history": tool_history,
        "conversation": conversation,
    }


# ------------------------------------------------------------
# Persistent wrapper now delegates to STRICT CORE
# ------------------------------------------------------------

_strict_core_agent = coder_agent_strict


def coder_agent_persistent(task, **kwargs):
    history = []

    try:
        if SESSION_FILE.exists():
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)

            if not isinstance(history, list):
                history = []
    except Exception:
        history = []

    result = _strict_core_agent(task, **kwargs)

    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "task": str(task),
        "status": result.get("status"),
        "skill": result.get("skill"),
        "steps": result.get("steps"),
        "state": result.get("state"),
        "decision": result.get("decision"),
        "inspected": result.get("inspected"),
        "modified": result.get("modified"),
        "verified": result.get("verified"),
        "tools": [
            {
                "tool": x.get("tool"),
                "state": x.get("state"),
                "success": (
                    x.get("result", {}).get("success")
                    if isinstance(x.get("result"), dict)
                    else None
                ),
            }
            for x in result.get("tool_history", [])
        ],
        "answer": result.get("answer", ""),
    }

    history.append(summary)
    history = history[-50:]

    try:
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    result["persistent"] = True
    return result


# Canonical public entry point.
coder_agent = coder_agent_persistent

# Explicit aliases for inspection/debugging.
coder_agent_core = coder_agent_strict
coder_agent_strict_core = coder_agent_strict

