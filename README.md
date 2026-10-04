# My-Agent

MyAgent-Coder persistent Colab bootstrap.

## One-command Google Colab startup

Run this single command inside a Google Colab notebook:

```python
exec(__import__("urllib.request").request.urlopen("https://loverof-darkness.github.io/My-Agent/colab_init.py").read())
```

The bootstrap:

1. Runs inside the Colab IPython kernel.
2. Mounts Google Drive.
3. Uses the persistent /content/drive/MyDrive/MyAgent-Coder backup.
4. Installs the required llama.cpp CUDA wheel when missing.
5. Reuses the existing Qwen2.5-Coder-14B singleton.
6. Loads the persistent agent runtime.
7. Exposes ac(message) as the single public entry point.

### Do not use

```bash
curl -sSL https://loverof-darkness.github.io/My-Agent/colab_init.py | python
```

That launches a separate Python process and cannot mount Google Drive through the active Colab kernel.

## GitHub Pages

GitHub Pages is deployed by .github/workflows/pages.yml.
The published bootstrap URL is:

https://loverof-darkness.github.io/My-Agent/colab_init.py

Google Drive remains the persistent backup for the full MyAgent-Coder runtime and model.
