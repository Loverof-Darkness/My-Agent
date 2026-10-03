# AUTOMATIC INIT FOR MYAGENT-CODER
import os
import sys
import subprocess
from pathlib import Path

print("=== MYAGENT-CODER INSTANT SETUP ===")

# 1. Mount Google Drive
if not os.path.exists('/content/drive'):
    print("Mounting Google Drive...")
    from google.colab import drive
    drive.mount('/content/drive')

# 2. Check for existence of the model configuration
config_path = Path('/content/drive/MyDrive/MyAgent-Coder/config/session_state.json')
if not config_path.exists():
    print("Configuring new workspace directory structural trees on Google Drive...")
    os.makedirs('/content/drive/MyDrive/MyAgent-Coder', exist_ok=True)

# 3. Fast boot bootstrap
bootstrap_path = '/content/drive/MyDrive/MyAgent-Coder/bootstrap.py'
if os.path.exists(bootstrap_path):
    print("Loading bootstrap process...")
    from IPython import get_ipython
    get_ipython().run_line_magic('run', bootstrap_path)
else:
    print("Fallback: Cloning GitHub repository layout...")
    subprocess.run(["git", "clone", "https://github.com/Loverof-Darkness/My-Agent.git", "/content/My-Agent"], check=True)
