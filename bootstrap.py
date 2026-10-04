"""MyAgent-Coder persistent bootstrap.

Runs inside the active Colab IPython kernel.
Google Drive is the persistent source for the agent runtime, model,
memory, state, and projects. The Qwen model is loaded exactly once
by the Drive start.py launcher and then reused here.
"""

import sys
import time
import subprocess
from pathlib import Path


ROOT = Path("/content/drive/MyDrive/MyAgent-Coder")
START_SCRIPT = ROOT / "start.py"
RUNTIME_SCRIPT = ROOT / "runtime" / "agent_runtime.py"


print("=" * 70)
print("MYAGENT-CODER — PERSISTENT BOOTSTRAP")
print("=" * 70)


# 1. Required Python dependency
try:
    import llama_cpp  # noqa: F401
    print("✓ llama-cpp-python already installed.")
except ImportError:
    print("Installing llama-cpp-python CUDA wheel...")
    print("Download/install progress is intentionally visible.")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-U",
            "--progress-bar",
            "on",
            "llama-cpp-python",
            "--extra-index-url",
            "https://abetlen.github.io/llama-cpp-python/whl/cu130",
        ],
        check=True,
    )
    print("✓ llama-cpp-python installed.")


# 2. Use the real Colab user namespace.
# This is important because objects created by start.py and
# agent_runtime.py must remain available to the notebook as ac(),
# coder_agent, qwen2_coder, etc.
from IPython import get_ipython

ip = get_ipython()

if ip is None:
    raise RuntimeError(
        "The MyAgent-Coder bootstrap must run inside a Colab/IPython kernel."
    )

user_ns = ip.user_ns


# 3. Execute the persistent model launcher IN the notebook namespace.
if not START_SCRIPT.is_file():
    raise FileNotFoundError(
        f"MyAgent-Coder start.py not found: {START_SCRIPT}"
    )

print("Loading/reusing persistent model launcher...")
ip.run_line_magic("run", f"-i {START_SCRIPT}")


# 4. Locate the already-loaded Qwen singleton.
MODEL = (
    user_ns.get("qwen2_coder")
    or user_ns.get("qwen_coder")
    or user_ns.get("model")
    or user_ns.get("llm")
)

if MODEL is None:
    raise RuntimeError(
        "Qwen model was not exposed by start.py. "
        "No second model will be allocated."
    )

print("✓ Existing Qwen model found.")
print(f"  Type: {type(MODEL).__name__}")


# 5. Provide compatibility globals BEFORE loading the runtime.
# Older Drive runtime copies may refer to time without importing it.
# The runtime inference backend expects QWEN to point at the singleton.
user_ns["time"] = time
user_ns["QWEN"] = MODEL
user_ns["qwen2_coder"] = MODEL
user_ns["qwen_coder"] = MODEL


# 6. Execute the agent runtime IN the same notebook namespace.
# Using -i makes runtime function globals resolve against the same
# namespace where QWEN/time and the loaded model already exist.
if not RUNTIME_SCRIPT.is_file():
    raise FileNotFoundError(
        f"MyAgent-Coder agent runtime not found: {RUNTIME_SCRIPT}"
    )

print("Loading persistent agent runtime...")
ip.run_line_magic("run", f"-i {RUNTIME_SCRIPT}")

# Reassert canonical singleton references after runtime startup.
user_ns["time"] = time
user_ns["QWEN"] = MODEL
user_ns["qwen2_coder"] = MODEL
user_ns["qwen_coder"] = MODEL


# 7. Select the unified public entry point.
router = user_ns.get("routed_coder_agent")

if callable(router):
    # Automatic CHAT <-> CODING routing.
    user_ns["ac"] = router
    user_ns["coder_agent"] = router
    public_mode = "automatic CHAT <-> CODING router"
else:
    coding_agent = user_ns.get("coder_agent_persistent")
    if not callable(coding_agent):
        coding_agent = user_ns.get("coder_agent")

    if not callable(coding_agent):
        raise RuntimeError(
            "Agent runtime loaded, but no supported agent entry point was found."
        )

    user_ns["ac"] = coding_agent
    user_ns["coder_agent"] = coding_agent
    public_mode = "coding agent only (router unavailable in Drive runtime)"


# 8. Optional Agent class
agent_status = (
    "Agent exported"
    if callable(user_ns.get("Agent"))
    else "Agent class not defined by runtime"
)


print("=" * 70)
print("MYAGENT-CODER READY")
print("=" * 70)
print("Public entry point : ac(message)")
print(f"Mode               : {public_mode}")
print(f"Model              : {type(MODEL).__name__}")
print(f"Workspace           : {ROOT / 'projects' / 'workspace'}")
print(f"Memory              : {ROOT / 'memory'}")
print(f"Skills              : {ROOT / 'agent' / 'skills' / 'Agent_Skills'}")
print(agent_status)
print("=" * 70)
