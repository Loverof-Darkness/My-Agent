"""MyAgent-Coder persistent bootstrap.

Runs inside the active Colab IPython kernel.

Google Drive is the persistent source for the agent runtime, model,
memory, state, and projects.

Before model startup this bootstrap synchronizes the small, versioned
Drive launcher/recovery scripts from the GitHub Pages build. This makes
the persistent Drive backup self-healing while keeping the large model
and user data on Google Drive.
"""

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path("/content/drive/MyDrive/MyAgent-Coder")
DRIVE_RUNTIME = ROOT / "runtime"
START_SCRIPT = ROOT / "start.py"
RUNTIME_SCRIPT = DRIVE_RUNTIME / "agent_runtime.py"

PAGES_BASE = "https://loverof-darkness.github.io/My-Agent"
SYNC_FILES = {
    "start.py": "MYAGENT-CODER-DRIVE-LAUNCHER-V2",
    "runtime/model_recovery.py": "MYAGENT-CODER-DRIVE-RECOVERY-V2",
}


def _download_with_progress(url, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {url}")
    subprocess.run(
        [
            "wget",
            "-c",
            "--show-progress",
            "-O",
            str(destination),
            url,
        ],
        check=True,
    )


def _copy_with_progress(source, destination):
    try:
        from tqdm.auto import tqdm
    except Exception:
        tqdm = None

    total = source.stat().st_size
    copied = 0
    destination.parent.mkdir(parents=True, exist_ok=True)

    with source.open("rb") as src, destination.open("wb") as dst:
        if tqdm is not None:
            with tqdm(
                total=total,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                desc=f"Backup {destination.name}",
            ) as bar:
                while True:
                    block = src.read(1024 * 1024)
                    if not block:
                        break
                    dst.write(block)
                    copied += len(block)
                    bar.update(len(block))
        else:
            while True:
                block = src.read(1024 * 1024)
                if not block:
                    break
                dst.write(block)
                copied += len(block)
                percent = copied * 100 / total if total else 100
                print(
                    f"\rBackup {destination.name}: {percent:6.2f}%",
                    end="",
                    flush=True,
                )
            print()

    shutil.copystat(source, destination)


def _sync_drive_bootstrap_files():
    """Install the versioned launcher/recovery into persistent Drive."""
    print("Synchronizing persistent Drive launcher files...")

    cache_root = Path("/content/MyAgent-Coder/bootstrap-cache")
    cache_root.mkdir(parents=True, exist_ok=True)

    for relative_path, marker in SYNC_FILES.items():
        target = ROOT / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)

        needs_update = True
        if target.is_file():
            try:
                current = target.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )
                needs_update = marker not in current
            except Exception:
                needs_update = True

        if not needs_update:
            print(f"✓ {relative_path} already current")
            continue

        # Preserve the existing Drive backup before replacing it.
        if target.is_file():
            backup = target.with_suffix(
                target.suffix + ".pre_v2_backup"
            )

            _copy_with_progress(target, backup)
            print(f"✓ Backup created: {backup}")

        source = cache_root / relative_path
        url = f"{PAGES_BASE}/{relative_path}"

        _download_with_progress(url, source)

        if not source.is_file() or source.stat().st_size == 0:
            raise RuntimeError(
                f"Downloaded empty/missing bootstrap file: {relative_path}"
            )

        _copy_with_progress(source, target)
        print(f"✓ Updated Drive: {target}")

        text = target.read_text(
            encoding="utf-8",
            errors="ignore",
        )
        if marker not in text:
            raise RuntimeError(
                f"Version marker missing after update: {relative_path}"
            )

    print("✓ Persistent Drive launcher synchronization complete.")


print("=" * 70)
print("MYAGENT-CODER — PERSISTENT BOOTSTRAP")
print("=" * 70)

# ------------------------------------------------------------
# 1. Require the Colab IPython kernel.
# ------------------------------------------------------------
from IPython import get_ipython

ip = get_ipython()

if ip is None:
    raise RuntimeError(
        "The MyAgent-Coder bootstrap must run inside a Colab/IPython kernel."
    )

user_ns = ip.user_ns


# ------------------------------------------------------------
# 2. Synchronize the Drive-side launcher before it can load the model.
#    This removes the expensive SHA-256 startup scan and makes ac()
#    available when start.py itself is executed.
# ------------------------------------------------------------
_sync_drive_bootstrap_files()


# ------------------------------------------------------------
# 3. Required Python dependency.
# ------------------------------------------------------------
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


# ------------------------------------------------------------
# 4. Run the Drive launcher in the actual notebook namespace.
# ------------------------------------------------------------
if not START_SCRIPT.is_file():
    raise FileNotFoundError(
        f"MyAgent-Coder start.py not found: {START_SCRIPT}"
    )

print("Loading/reusing persistent Qwen launcher...")
ip.run_line_magic("run", f"-i {START_SCRIPT}")


# ------------------------------------------------------------
# 5. Recover the existing Qwen singleton from the notebook namespace.
# ------------------------------------------------------------
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

print("✓ Existing Qwen model available.")
print(f"  Type: {type(MODEL).__name__}")


# ------------------------------------------------------------
# 6. Load the persistent agent runtime into the same namespace.
# ------------------------------------------------------------
if not RUNTIME_SCRIPT.is_file():
    raise FileNotFoundError(
        f"Agent runtime not found: {RUNTIME_SCRIPT}"
    )

user_ns["QWEN"] = MODEL
user_ns["qwen2_coder"] = MODEL
user_ns["qwen_coder"] = MODEL

print("Loading persistent agent runtime...")
ip.run_line_magic("run", f"-i {RUNTIME_SCRIPT}")


# ------------------------------------------------------------
# 7. Export the single user-facing API.
# ------------------------------------------------------------
router = user_ns.get("routed_coder_agent")

if not callable(router):
    raise RuntimeError(
        "Agent runtime loaded, but routed_coder_agent is unavailable."
    )

user_ns["ac"] = router
user_ns["coder_agent"] = router
user_ns["QWEN"] = MODEL


print("=" * 70)
print("MYAGENT-CODER READY")
print("=" * 70)
print("Public entry point : ac(message)")
print("Mode               : automatic CHAT <-> CODING")
print(f"Model              : {type(MODEL).__name__}")
print(f"Workspace           : {ROOT / 'projects' / 'workspace'}")
print(f"Memory              : {ROOT / 'memory'}")
print(f"Skills              : {ROOT / 'agent' / 'skills' / 'Agent_Skills'}")
print("SHA-256 startup scan: DISABLED")
print("=" * 70)
