"""MyAgent-Coder Colab bootstrap.

This file is designed to be fetched from GitHub Pages and executed
inside a Google Colab notebook with exec(...). It must not be piped
into a standalone Python subprocess because google.colab.drive.mount()
needs the active Colab IPython kernel.
"""

from pathlib import Path


GITHUB_PAGES_URL = (
    "https://loverof-darkness.github.io/My-Agent/colab_init.py"
)
DRIVE_ROOT = Path("/content/drive/MyDrive/MyAgent-Coder")
BOOTSTRAP_PATH = DRIVE_ROOT / "bootstrap.py"


def _get_ipython_shell():
    try:
        from IPython import get_ipython
    except Exception:
        return None
    return get_ipython()


print("=" * 70)
print("MYAGENT-CODER — INSTANT COLAB STARTUP")
print("=" * 70)

ip = _get_ipython_shell()

if ip is None:
    raise RuntimeError(
        "\nMyAgent-Coder must be executed inside a Google Colab notebook.\n"
        "Do NOT use: curl ... | python\n\n"
        "Use this single Colab command instead:\n"
        "exec(__import__('urllib.request').request.urlopen("
        f"'{GITHUB_PAGES_URL}'"
        ").read())"
    )

try:
    from google.colab import drive
except Exception as exc:
    raise RuntimeError(
        "Google Colab APIs are unavailable. Run this bootstrap from a "
        "Google Colab notebook."
    ) from exc

if not Path("/content/drive/MyDrive").is_dir():
    print("Mounting Google Drive...")
    drive.mount("/content/drive")
else:
    print("✓ Google Drive already mounted.")

DRIVE_ROOT.mkdir(parents=True, exist_ok=True)

if not BOOTSTRAP_PATH.is_file():
    raise FileNotFoundError(
        "\nMyAgent-Coder backup is incomplete. Missing:\n"
        f"  {BOOTSTRAP_PATH}\n\n"
        "Restore the MyAgent-Coder backup to Google Drive first."
    )

print(f"✓ Persistent agent backup found: {DRIVE_ROOT}")
print("Starting persistent MyAgent-Coder bootstrap...")

ip.run_line_magic("run", str(BOOTSTRAP_PATH))

print("=" * 70)
print("MYAGENT-CODER STARTUP COMPLETE")
print("=" * 70)
