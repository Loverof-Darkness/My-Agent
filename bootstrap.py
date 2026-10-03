# AUTOMATIC BOOTSTRAP FOR MYAGENT-CODER
import os
import sys
import subprocess

print("=== MYAGENT-CODER INSTANT BOOTSTRAP ===")

# 1. Install llama-cpp-python precompiled wheel
try:
    import llama_cpp
    print("✓ llama-cpp-python already installed.")
except ImportError:
    print("Installing precompiled GPU wheels...")
    subprocess.run([
        "pip", "install", "-q", "-U", "llama-cpp-python",
        "--extra-index-url", "https://abetlen.github.io/llama-cpp-python/whl/cu130"
    ], check=True)
    print("✓ Wheel installed successfully.")

# 2. Execute startup routines
start_script = "/content/drive/MyDrive/MyAgent-Coder/start.py"
if os.path.exists(start_script):
    print("Starting model singleton...")
    # We execute in the main namespace
    from IPython import get_ipython
    get_ipython().run_line_magic("run", start_script)
else:
    print("Error: start.py not found on Google Drive!")
