"""
MyAgent-Coder — Persistent Qwen Model Recovery

Architecture:

Google Drive
    MASTER MODEL
        |
        v
Colab /content
    RUNTIME CACHE

The Drive copy is NEVER deleted by this module.
"""

import os
import shutil
import hashlib
import json
import subprocess
from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

DRIVE_MODEL = (
    "/content/drive/MyDrive/MyAgent-Coder/models/"
    "qwen2.5-coder-14b/"
    "qwen2.5-coder-14b-instruct-q4_k_m.gguf"
)

LOCAL_DIR = (
    "/content/MyAgent-Coder/models/"
    "qwen2.5-coder-14b"
)

LOCAL_MODEL = os.path.join(
    LOCAL_DIR,
    "qwen2.5-coder-14b-instruct-q4_k_m.gguf"
)

MANIFEST = (
    "/content/drive/MyDrive/MyAgent-Coder/models/"
    "qwen2.5-coder-14b/"
    "model_manifest.json"
)

MODEL_URL = (
    "https://huggingface.co/Qwen/Qwen2.5-Coder-14B-Instruct-GGUF"
    "/resolve/main/qwen2.5-coder-14b-instruct-q4_k_m.gguf"
)

MIN_MODEL_SIZE = 8 * 1024**3


# ============================================================
# HASH
# ============================================================

def sha256_file(path, chunk_size=16 * 1024 * 1024):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


# ============================================================
# DOWNLOAD DRIVE MASTER
# ============================================================

def ensure_drive_master(verbose=True):

    os.makedirs(os.path.dirname(DRIVE_MODEL), exist_ok=True)

    if os.path.isfile(DRIVE_MODEL):

        size = os.path.getsize(DRIVE_MODEL)

        if size >= MIN_MODEL_SIZE:

            if verbose:
                print("✓ Drive master already exists")
                print(
                    f"  {size / (1024**3):.3f} GiB"
                )

            return DRIVE_MODEL

        # Invalid/truncated Drive file.
        # Only the MASTER file itself may be replaced.
        if verbose:
            print("⚠ Drive master is too small.")
            print("  Re-downloading it.")

        os.remove(DRIVE_MODEL)

    if verbose:
        print("\nDownloading Qwen2.5-Coder 14B to Google Drive...")
        print("Destination:")
        print(DRIVE_MODEL)
        print("\nProgress:\n")

    result = subprocess.run([
        "curl",
        "-L",
        "--fail",
        "--retry", "5",
        "--retry-delay", "5",
        "--progress-bar",
        "-C", "-",
        MODEL_URL,
        "-o", DRIVE_MODEL,
    ])

    if result.returncode != 0:
        raise RuntimeError(
            "Failed to download the Drive master. "
            f"curl exit code: {result.returncode}"
        )

    size = os.path.getsize(DRIVE_MODEL)

    if size < MIN_MODEL_SIZE:
        raise RuntimeError(
            "Downloaded Drive master is unexpectedly small: "
            f"{size / (1024**3):.3f} GiB"
        )

    if verbose:
        print("\n✓ Drive master downloaded")
        print(f"  {size / (1024**3):.3f} GiB")

    return DRIVE_MODEL


# ============================================================
# RESTORE LOCAL CACHE
# ============================================================

def ensure_local_cache(verbose=True):

    # NEVER modify Drive master here.
    if not os.path.isfile(DRIVE_MODEL):
        ensure_drive_master(verbose=verbose)

    drive_size = os.path.getsize(DRIVE_MODEL)

    os.makedirs(LOCAL_DIR, exist_ok=True)

    local_valid = False

    if os.path.isfile(LOCAL_MODEL):

        local_size = os.path.getsize(LOCAL_MODEL)

        if local_size == drive_size:
            local_valid = True

            if verbose:
                print(
                    f"\n✓ Local model already present "
                    f"({local_size / (1024**3):.3f} GiB)"
                )

    if not local_valid:

        if os.path.isfile(LOCAL_MODEL):
            if verbose:
                print("\n⚠ Invalid local cache detected.")
                print("  Replacing local cache.")

            os.remove(LOCAL_MODEL)

        if verbose:
            print("\nRestoring model:")
            print(f"  FROM: {DRIVE_MODEL}")
            print(f"  TO  : {LOCAL_MODEL}")
            print("\nProgress:\n")

        result = subprocess.run([
            "rsync",
            "-ah",
            "--info=progress2",
            DRIVE_MODEL,
            LOCAL_MODEL,
        ])

        if result.returncode != 0:
            raise RuntimeError(
                "Failed to restore local model. "
                f"rsync exit code: {result.returncode}"
            )

    local_size = os.path.getsize(LOCAL_MODEL)

    if local_size != drive_size:
        raise RuntimeError(
            "Model size mismatch after restore.\n"
            f"Drive: {drive_size}\n"
            f"Local: {local_size}"
        )

    return LOCAL_MODEL


# ============================================================
# INTEGRITY CHECK
# ============================================================

def verify_model_integrity(verbose=True):

    if not os.path.isfile(DRIVE_MODEL):
        raise FileNotFoundError(
            "Drive master does not exist."
        )

    if not os.path.isfile(LOCAL_MODEL):
        raise FileNotFoundError(
            "Local model does not exist."
        )

    drive_size = os.path.getsize(DRIVE_MODEL)
    local_size = os.path.getsize(LOCAL_MODEL)

    if drive_size != local_size:
        raise RuntimeError(
            "Model size mismatch."
        )

    if verbose:
        print("\nCalculating SHA-256...")
        print("This may take some time.")

    drive_hash = sha256_file(DRIVE_MODEL)
    local_hash = sha256_file(LOCAL_MODEL)

    if drive_hash != local_hash:
        raise RuntimeError(
            "MODEL INTEGRITY FAILURE\n"
            "Drive and local SHA-256 hashes differ."
        )

    manifest = {
        "model": "Qwen2.5-Coder-14B-Instruct-GGUF",
        "filename": os.path.basename(DRIVE_MODEL),
        "drive_master": DRIVE_MODEL,
        "local_cache": LOCAL_MODEL,
        "size_bytes": drive_size,
        "sha256": drive_hash,
        "verified_at": datetime.now().isoformat(),
        "policy": {
            "drive_is_master": True,
            "local_is_cache": True,
            "restore_if_missing": True,
            "replace_if_size_mismatch": True,
            "verify_sha256": True,
            "never_delete_drive_master": True,
        },
    }

    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)

    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    if verbose:
        print("✓ SHA-256 verified")
        print(f"  {drive_hash}")
        print(f"✓ Manifest updated")
        print(f"  {MANIFEST}")

    return {
        "drive_model": DRIVE_MODEL,
        "local_model": LOCAL_MODEL,
        "size_bytes": drive_size,
        "sha256": drive_hash,
        "verified": True,
    }


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def prepare_model(verbose=True):

    if verbose:
        print("=" * 70)
        print("MYAGENT-CODER — MODEL RECOVERY")
        print("=" * 70)

        print("\nMASTER:")
        print(f"  {DRIVE_MODEL}")

        print("\nCACHE:")
        print(f"  {LOCAL_MODEL}")

    ensure_drive_master(verbose=verbose)
    ensure_local_cache(verbose=verbose)
    result = verify_model_integrity(verbose=verbose)

    if verbose:
        print("\n" + "=" * 70)
        print("MODEL READY")
        print("=" * 70)

    return result
