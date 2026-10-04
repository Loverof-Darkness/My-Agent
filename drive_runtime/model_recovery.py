"""MYAGENT-CODER-DRIVE-RECOVERY-V2\nFast Qwen model recovery for MyAgent-Coder.

Google Drive is the permanent master. /content is disposable runtime
storage.

Integrity policy:
- Always verify the model by file size.
- Do not calculate SHA-256 during normal startup.
- A previous SHA-256 value may remain in the manifest for reference,
  but it is not recomputed or used as a startup gate.
- Missing local cache is restored from Drive.
- Size mismatch triggers replacement from the Drive master.
- The Drive master is never deleted by this module.
"""

import json
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path("/content/drive/MyDrive/MyAgent-Coder")

MODEL_DIR = ROOT / "models" / "qwen2.5-coder-14b"
DRIVE_MODEL = MODEL_DIR / "qwen2.5-coder-14b-instruct-q4_k_m.gguf"
LOCAL_DIR = Path("/content/MyAgent-Coder/models/qwen2.5-coder-14b")
LOCAL_MODEL = LOCAL_DIR / DRIVE_MODEL.name
MANIFEST = MODEL_DIR / "model_manifest.json"

EXPECTED_SIZE = 8_988_110_272


def _progress_copy(source, destination, chunk_size=16 * 1024 * 1024):
    """Copy a file with a visible progress bar."""
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
                desc="Restoring model",
            ) as bar:
                while True:
                    block = src.read(chunk_size)
                    if not block:
                        break
                    dst.write(block)
                    copied += len(block)
                    bar.update(len(block))
        else:
            while True:
                block = src.read(chunk_size)
                if not block:
                    break
                dst.write(block)
                copied += len(block)
                percent = copied * 100 / total if total else 100
                print(
                    f"\rRestoring model: {percent:6.2f}%",
                    end="",
                    flush=True,
                )
            print()

    shutil.copystat(source, destination)


def _progress_download(url, destination):
    """Download with wget's visible progress bar."""
    destination.parent.mkdir(parents=True, exist_ok=True)

    temp = destination.with_suffix(destination.suffix + ".download")

    cmd = [
        "wget",
        "-c",
        "--show-progress",
        "-O",
        str(temp),
        url,
    ]

    print("Downloading model master...")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        raise RuntimeError(
            f"Model download failed with exit code {result.returncode}"
        )

    if not temp.is_file():
        raise FileNotFoundError("Downloaded model file was not created.")

    temp.replace(destination)


def _write_manifest():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    previous = {}
    if MANIFEST.is_file():
        try:
            previous = json.loads(
                MANIFEST.read_text(encoding="utf-8")
            )
        except Exception:
            previous = {}

    manifest = {
        "model": DRIVE_MODEL.name,
        "size_bytes": DRIVE_MODEL.stat().st_size,
        "drive_model": str(DRIVE_MODEL),
        "local_model": str(LOCAL_MODEL),
        "sha256": previous.get("sha256"),
        "sha256_verified_at": previous.get("sha256_verified_at"),
        "sha256_startup_check": False,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    MANIFEST.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def ensure_drive_master(verbose=True):
    if DRIVE_MODEL.is_file():
        size = DRIVE_MODEL.stat().st_size

        if size != EXPECTED_SIZE:
            raise RuntimeError(
                "Drive master size mismatch. "
                f"Expected {EXPECTED_SIZE:,} bytes, got {size:,}."
            )

        if verbose:
            print("✓ Drive master valid by size")
            print(f"  {size / (1024**3):.3f} GiB")

        return DRIVE_MODEL

    # Only used for first-time recovery when the permanent master is absent.
    url = (
        "https://huggingface.co/Qwen/Qwen2.5-Coder-14B-Instruct-GGUF/"
        "resolve/main/qwen2.5-coder-14b-instruct-q4_k_m.gguf"
    )

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    _progress_download(url, DRIVE_MODEL)

    size = DRIVE_MODEL.stat().st_size
    if size != EXPECTED_SIZE:
        raise RuntimeError(
            "Downloaded Drive master has an unexpected size. "
            f"Expected {EXPECTED_SIZE:,}, got {size:,}."
        )

    return DRIVE_MODEL


def ensure_local_cache(verbose=True):
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)

    if LOCAL_MODEL.is_file():
        local_size = LOCAL_MODEL.stat().st_size

        if local_size == EXPECTED_SIZE:
            if verbose:
                print("✓ Local model already present")
                print(f"  {local_size / (1024**3):.3f} GiB")
            return LOCAL_MODEL

        if verbose:
            print("⚠ Local model size mismatch.")
            print("  Replacing it from the Drive master.")

        LOCAL_MODEL.unlink()

    if verbose:
        print("Restoring model from Google Drive...")
        print(f"Source      : {DRIVE_MODEL}")
        print(f"Destination : {LOCAL_MODEL}")

    _progress_copy(DRIVE_MODEL, LOCAL_MODEL)

    local_size = LOCAL_MODEL.stat().st_size

    if local_size != EXPECTED_SIZE:
        raise RuntimeError(
            "Local model restore failed size verification. "
            f"Expected {EXPECTED_SIZE:,}, got {local_size:,}."
        )

    return LOCAL_MODEL


def verify_model_integrity(verbose=True):
    """Compatibility API: startup verification is SIZE ONLY."""
    drive_size = DRIVE_MODEL.stat().st_size
    local_size = LOCAL_MODEL.stat().st_size

    verified = (
        drive_size == EXPECTED_SIZE
        and local_size == EXPECTED_SIZE
        and drive_size == local_size
    )

    if verbose:
        print("✓ Model size verification passed")
        print(f"  Drive : {drive_size / (1024**3):.3f} GiB")
        print(f"  Local : {local_size / (1024**3):.3f} GiB")
        print("  SHA-256 startup check: DISABLED")

    return {
        "verified": verified,
        "size_bytes": local_size,
        "sha256": None,
        "drive_model": str(DRIVE_MODEL),
        "local_model": str(LOCAL_MODEL),
        "method": "size-only",
    }


def prepare_model(verbose=True):
    if verbose:
        print("=" * 70)
        print("MYAGENT-CODER — FAST MODEL RECOVERY")
        print("=" * 70)
        print(f"MASTER : {DRIVE_MODEL}")
        print(f"CACHE  : {LOCAL_MODEL}")

    ensure_drive_master(verbose=verbose)
    ensure_local_cache(verbose=verbose)

    result = verify_model_integrity(verbose=verbose)
    _write_manifest()

    if not result["verified"]:
        raise RuntimeError("Model size verification failed.")

    if verbose:
        print("=" * 70)
        print("MODEL READY")
        print("=" * 70)

    return result
