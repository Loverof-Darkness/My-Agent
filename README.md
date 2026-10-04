# MyAgent-Coder

Persistent AI coding and conversational agent for Google Colab, powered by Qwen2.5-Coder-14B and backed by Google Drive.

## What this repository does

This repository is the lightweight **GitHub bootstrap layer** for MyAgent-Coder.

**GitHub contains:**
- The Colab bootstrap script.
- The persistent runtime bootstrap.
- GitHub Pages deployment configuration.
- Documentation.

**Google Drive contains the persistent MyAgent-Coder installation and backup:**
- Qwen2.5-Coder-14B model.
- Agent runtime.
- Tools.
- Agent_Skills.
- Memory.
- State.
- Logs.
- Workspace/projects.
- Recovery and integrity data.

The large GGUF model is intentionally kept out of GitHub.

Small Drive-side launcher/recovery scripts are synchronized automatically from the GitHub Pages build so the persistent Drive backup receives launcher fixes without replacing the large model or user data.

## One-command startup

Open a **new Google Colab notebook**, then run this **single Python line**:

```python
exec(__import__("urllib.request").request.urlopen("https://loverof-darkness.github.io/My-Agent/colab_init.py").read())
```

That is the intended user-facing startup command.

After startup completes, use:

```python
ac("Hello")
```

or:

```python
ac("Hey, how are you?")
```

## Important: do not use `curl | python`

Do **not** start the agent with:

```bash
curl -sSL https://loverof-darkness.github.io/My-Agent/colab_init.py | python
```

That executes the bootstrap in a separate Python process. Google Colab's `google.colab.drive.mount()` needs the active Colab IPython kernel, so the bootstrap must execute inside the notebook.

Use the one-line `exec(...)` command above instead.

## Startup flow

```text
New Google Colab notebook
        |
        v
One-line GitHub Pages bootstrap
        |
        v
Colab IPython kernel
        |
        v
Mount Google Drive
        |
        v
Persistent MyAgent-Coder backup
        |
        +--> fast model recovery (size check only, no SHA-256 startup scan)
        |
        +--> runtime recovery
        |
        +--> memory / state
        |
        +--> Agent_Skills
        |
        v
Reuse existing Qwen2.5-Coder singleton
        |
        v
Load agent runtime
        |
        v
Expose ac(message)
        |
        v
Automatic CHAT <-> CODING routing
```

## Normal chat and coding

`ac(message)` is the single public interface.

### Normal conversation

Examples:

```python
ac("Hey, how are you?")
ac("Explain HPLC system suitability.")
ac("What is Python?")
ac("Calculate 25% of 800.")
```

These should be handled as normal conversation without unnecessarily entering the coding tool workflow.

### Coding tasks

Examples:

```python
ac("Inspect my repository.")
ac("Find why the test is failing.")
ac("Fix the bug in test_project/hello.py")
ac("Run the tests.")
```

Coding requests are automatically routed to the coding workflow.

## Coding workflow

Coding tasks use the strict state machine:

```text
INSPECT
   |
DECIDE
   |
MODIFY
   |
VERIFY
   |
REPAIR (bounded)
   |
VERIFY
   |
FINAL
```

The agent must not claim a change or verification succeeded without actual tool evidence.

## Persistent Google Drive layout

The expected persistent root is:

```text
/content/drive/MyDrive/MyAgent-Coder/
├── models/
├── runtime/
├── agent/
│   └── skills/
│       └── Agent_Skills/
├── memory/
├── logs/
├── state/
├── indexes/
└── projects/
    └── workspace/
```

Google Drive is the long-term source of truth.

`/content` is treated as disposable Colab runtime storage.

If the local model cache is missing or invalid, the recovery layer restores it from the Drive master and verifies the expected file size. SHA-256 is not recalculated during normal startup because hashing the 8+ GiB model adds unnecessary startup time.

## Qwen2.5-Coder-14B

Expected permanent model:

```text
/content/drive/MyDrive/MyAgent-Coder/models/qwen2.5-coder-14b/qwen2.5-coder-14b-instruct-q4_k_m.gguf
```

Expected runtime cache:

```text
/content/MyAgent-Coder/models/qwen2.5-coder-14b/qwen2.5-coder-14b-instruct-q4_k_m.gguf
```

The launcher must reuse an already-loaded compatible Qwen instance instead of allocating a second copy, because the free Colab T4 has limited VRAM.

## Agent_Skills

The coding methodology source of truth is:

https://github.com/Loverof-Darkness/Agent_Skills

Relevant skills are selected for the task, and the smallest applicable `SKILL.md` is loaded before substantial development work.

Typical routing includes:

- `investigate` for bugs and root-cause analysis.
- `plan-eng-review` for architecture and implementation planning.
- `qa` for testing and verification.
- `review` for code and diff review.
- `cso` for security review.
- `setup-deploy` and `ship` for deployment/release workflows.

Claude-only runtime hooks or binaries from upstream gstack instructions must not be assumed to exist in Colab.

## GitHub Pages deployment

GitHub Pages is deployed by GitHub Actions.

Workflow:

```text
.github/workflows/pages.yml
```

The workflow:
1. Checks out the repository.
2. Validates the bootstrap Python files.
3. Builds a small Pages site.
4. Publishes `colab_init.py`.
5. Deploys the site with GitHub Pages Actions.

### Enable Pages

In GitHub:

```text
Repository Settings
  -> Pages
  -> Build and deployment
  -> Source
  -> GitHub Actions
```

The public bootstrap URL is:

```text
https://loverof-darkness.github.io/My-Agent/colab_init.py
```

If the repository owner or branch changes, update the bootstrap URL and workflow consistently.

## GitHub Personal Access Token

A GitHub PAT is **not required just to start the public Colab bootstrap**.

A PAT may be required for private GitHub operations such as authenticated repository access or pushing changes.

Never put a PAT, API key, password, private key, or other secret in:
- `README.md`
- `colab_init.py`
- `bootstrap.py`
- Git history
- GitHub Pages output

For Colab, keep secrets in a secure mechanism such as Colab Secrets or another appropriate secret store.

## Security rules

The coding runtime uses controlled filesystem and command tools.

Do not remove or weaken its safety restrictions just to make a test pass.

Destructive shell access, unrestricted filesystem access, and automatic GitHub pushes must not be enabled without explicit design and verification.

## Repository architecture

```text
My-Agent/
├── colab_init.py
├── bootstrap.py
├── runtime/
├── .github/
│   └── workflows/
│       └── pages.yml
└── README.md
```

The repository is intentionally small. The persistent and larger parts of MyAgent-Coder live in Google Drive.

## Fresh-Colab usage

For a completely new Colab runtime:

1. Create/open a Google Colab notebook.
2. Run the one-line startup command from this README.
3. Authorize Google Drive when Colab asks.
4. Wait for the `MYAGENT-CODER READY` message.
5. Start using `ac("...")`.

Example:

```python
exec(__import__("urllib.request").request.urlopen("https://loverof-darkness.github.io/My-Agent/colab_init.py").read())
ac("Hey, how are you?")
```

## Troubleshooting

### Google Drive mount error

If you see:

```text
AttributeError: 'NoneType' object has no attribute 'kernel'
```

you probably executed the bootstrap with `curl | python`.

Run the one-line Colab `exec(...)` command instead.

### `ac` is missing

Startup is not complete. Do not manually create a second model instance.

Check the `MYAGENT-CODER READY` output and the persistent Drive runtime.

### CUDA out-of-memory

Do not load another Qwen model in the same runtime. Restarting the runtime may be necessary if an incompatible or duplicate model is already resident.

### Missing Drive backup

The bootstrap expects:

```text
/content/drive/MyDrive/MyAgent-Coder/bootstrap.py
/content/drive/MyDrive/MyAgent-Coder/start.py
/content/drive/MyDrive/MyAgent-Coder/runtime/agent_runtime.py
```

Restore the persistent MyAgent-Coder backup before starting.

## Development rules

When changing this project:

1. Inspect the current repository first.
2. Use the relevant Agent_Skills instructions.
3. Fix root causes rather than stacking temporary workarounds.
4. Preserve the Qwen singleton model-loading policy.
5. Keep secrets out of the repository.
6. Validate Python syntax and relevant behavior before declaring success.
7. Do not claim deployment or external actions succeeded without evidence.

## Current intended user experience

```text
New Colab
   |
   +--> one line from this README
   |
   +--> Google Drive mounted
   |
   +--> persistent agent recovered
   |
   +--> Qwen loaded/reused
   |
   +--> ac() available
   |
   +--> normal chat OR automatic coding mode
```

The goal is simple: **one startup line, persistent Drive-backed agent, and one `ac()` interface for both conversation and coding.**


## Drive backup launcher

The persistent Drive backup contains its own `start.py` launcher. After the GitHub bootstrap has run once, the Drive launcher is upgraded to the current version and exports:

```python
ac("Hello")
```

It also starts the automatic CHAT <-> CODING router.

The Drive-side model recovery now uses a fast **size-only** startup check. It does not recalculate SHA-256 on every fresh Colab session. A previous SHA-256 value can remain in the model manifest for reference, but it is not used as a startup gate.

This change is intentional: calculating a SHA-256 over the 8+ GiB GGUF on every new runtime causes avoidable startup delay.

### Direct Drive startup

After the persistent Drive launcher has been synchronized, a notebook can also start it directly with:

```python
%run /content/drive/MyDrive/MyAgent-Coder/start.py
```

The launcher exports `qwen2_coder`, `qwen_coder`, `model`, `llm`, `QWEN`, and `ac` into the Colab notebook namespace.

### Recovery policy

```text
Drive model exists and expected size matches
        -> skip model copy
        -> no SHA-256 scan
        -> load/reuse Qwen

Local model missing
        -> copy Drive -> /content with progress
        -> size check
        -> load/reuse Qwen

Local model size mismatch
        -> replace from Drive
        -> size check
        -> load/reuse Qwen

Drive master missing
        -> download with visible progress
        -> size check
        -> use as permanent master
```
