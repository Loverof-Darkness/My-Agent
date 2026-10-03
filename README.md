# 🚀 My-Agent: Automated Multi-Modal Coding Agent Workspace

This repository hosts the portable runtime environment and bootstrap initialization setup for **MyAgent-Coder** — an autonomous software engineering and conversational agent powered by Qwen-2.5-Coder (14B).

## 🛠️ Instant Google Colab Installation
To automatically spin up your workspace, mount Google Drive, install pre-compiled GPU wheels, and launch the dynamic routing runtime in a single action, execute the following command in any Google Colab notebook:

```bash
!curl -sSL https://loverof-darkness.github.io/My-Agent/colab_init.py | python
```

## 📦 File Architecture
* **`colab_init.py`** — The global bootstrap entry point hosted on GitHub Pages.
* **`bootstrap.py`** — Instant GPU-accelerated dependencies and singleton loader.
* **`runtime/`** — State-machine workflows, diagnostic verification layers, and core agent modules.
* **`.gitignore`** — Keeps the repository clean by excluding massive 8.3GB GGUF model binaries.
