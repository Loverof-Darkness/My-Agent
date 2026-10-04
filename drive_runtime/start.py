"""Persistent MyAgent-Coder Colab launcher.

This launcher lives in Google Drive and is safe to execute with IPython
%run from a Colab notebook. It reuses an already-loaded Qwen singleton,
loads the persistent agent runtime into the notebook namespace, and
exports the single public entry point: ac(message).

Model recovery is size-based. SHA-256 hashing is intentionally disabled
to avoid rescanning the 8+ GiB model on every fresh Colab session.
"""

import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path("/content/drive/MyDrive/MyAgent-Coder")
RUNTIME = ROOT / "runtime" / "agent_runtime.py"
RECOVERY = ROOT / "runtime" / "model_recovery.py"

MODEL_NAME = "qwen2.5-coder-14b-instruct-q4_k_m.gguf"
LOCAL_MODEL = Path("/content/MyAgent-Coder/models/qwen2.5-coder-14b") / MODEL_NAME


def _ipython():
    try:
        from IPython import get_ipython
        return get_ipython()
    except Exception:
        return None


def _user_namespace():
    ip = _ipython()
    if ip is None:
        return globals()
    return ip.user_ns


def _find_loaded_qwen(namespace):
    """Return a compatible already-loaded llama_cpp Llama instance."""
    expected_name = MODEL_NAME

    for value in list(namespace.values()):
        if value is None:
            continue
        if value.__class__.__name__ != "Llama":
            continue

        model_path = getattr(value, "model_path", None)
        if model_path:
            try:
                if Path(str(model_path)).name == expected_name:
                    return value
            except Exception:
                pass

    return None


def _load_module_from_drive(path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module: {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_qwen_model():
    """Prepare the local model and reuse/load exactly one Qwen instance."""
    namespace = _user_namespace()

    existing = _find_loaded_qwen(namespace)
    if existing is not None:
        namespace["model"] = existing
        namespace["llm"] = existing
        namespace["qwen2_coder"] = existing
        namespace["qwen_coder"] = existing
        namespace["QWEN"] = existing
        return existing

    if not RECOVERY.is_file():
        raise FileNotFoundError(f"Model recovery module not found: {RECOVERY}")

    recovery = _load_module_from_drive(
        RECOVERY,
        "myagent_drive_model_recovery",
    )

    verification = recovery.prepare_model(verbose=True)
    if not verification.get("verified"):
        raise RuntimeError(
            "Model recovery failed. No model instance will be allocated."
        )

    model_path = verification["local_model"]

    if not Path(model_path).is_file():
        raise FileNotFoundError(f"Local model not found: {model_path}")

    from llama_cpp import Llama

    print("=" * 70)
    print("MYAGENT-CODER — MODEL LOAD")
    print("=" * 70)
    print(f"Model : {model_path}")
    print("GPU   : llama.cpp CUDA")
    print("Mode  : singleton + size verification")
    print()

    model = Llama(
        model_path=str(model_path),
        n_gpu_layers=-1,
        n_ctx=8192,
        n_batch=512,
        n_threads=2,
        n_threads_batch=2,
        verbose=True,
    )

    namespace["model"] = model
    namespace["llm"] = model
    namespace["qwen2_coder"] = model
    namespace["qwen_coder"] = model
    namespace["QWEN"] = model

    return model


def load_agent_runtime(model=None):
    """Load agent_runtime.py into the current Colab user namespace."""
    namespace = _user_namespace()

    if model is None:
        model = (
            namespace.get("qwen2_coder")
            or namespace.get("qwen_coder")
            or namespace.get("model")
            or namespace.get("llm")
        )

    if model is None:
        raise RuntimeError("Qwen model is not available.")

    namespace["QWEN"] = model
    namespace["qwen2_coder"] = model
    namespace["qwen_coder"] = model

    if not RUNTIME.is_file():
        raise FileNotFoundError(
            f"Agent runtime not found: {RUNTIME}"
        )

    ip = _ipython()

    if ip is None:
        raise RuntimeError(
            "MyAgent-Coder must be started from a Colab/IPython notebook."
        )

    print("Loading persistent agent runtime...")
    ip.run_line_magic("run", f"-i {RUNTIME}")

    # Runtime has now defined routed_coder_agent in the same notebook.
    router = namespace.get("routed_coder_agent")

    if not callable(router):
        raise RuntimeError(
            "agent_runtime.py loaded, but routed_coder_agent was not exported."
        )

    namespace["coder_agent"] = router
    namespace["ac"] = router
    namespace["QWEN"] = model

    return router


def start(load_model=True):
    print("=" * 70)
    print("MYAGENT-CODER — DRIVE STARTUP")
    print("=" * 70)

    namespace = _user_namespace()

    if load_model:
        model = load_qwen_model()
    else:
        model = (
            namespace.get("qwen2_coder")
            or namespace.get("qwen_coder")
            or namespace.get("model")
            or namespace.get("llm")
        )

    if model is None:
        raise RuntimeError("No Qwen model is available.")

    agent = load_agent_runtime(model)

    print("=" * 70)
    print("MYAGENT-CODER READY")
    print("=" * 70)
    print(f"Model              : {type(model).__name__}")
    print("Public entry point : ac(message)")
    print("Mode               : automatic CHAT <-> CODING")
    print(f"Workspace          : {ROOT / 'projects' / 'workspace'}")
    print(f"Memory             : {ROOT / 'memory'}")
    print(f"Skills             : {ROOT / 'agent' / 'skills' / 'Agent_Skills'}")
    print("=" * 70)

    return {
        "model": model,
        "agent": agent,
        "ac": agent,
    }


if __name__ == "__main__":
    start(load_model=True)
