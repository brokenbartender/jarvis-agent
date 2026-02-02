from __future__ import annotations

import os

from interpreter import interpreter

from .config import Settings


def _get_ollama_models(base: str) -> list[str]:
    try:
        import urllib.request
        import json as _json

        with urllib.request.urlopen(f"{base}/api/tags", timeout=2) as resp:
            if resp.status != 200:
                return []
            data = _json.loads(resp.read().decode("utf-8", errors="ignore"))
            return [m.get("name") for m in data.get("models", []) if m.get("name")]
    except Exception:
        return []


def _pick_small_ollama_model(models: list[str]) -> str | None:
    preferences = [
        "gemma:2b",
        "llama3.2:1b",
        "llama3.2:3b",
        "phi3:mini",
        "qwen2.5:1.5b",
        "llama3.2",
        "llama3.1",
    ]
    for pref in preferences:
        if pref in models:
            return pref
    return models[0] if models else None


def configure_interpreter(settings: Settings) -> None:
    # Patch missing display helper in some open-interpreter versions.
    try:
        import interpreter.core.respond as respond_mod

        if not hasattr(respond_mod, "display_markdown_message"):
            respond_mod.display_markdown_message = lambda *args, **kwargs: None
    except Exception:
        pass

    # Prefer OpenAI (ChatGPT) when key is present.
    if os.getenv("OPENAI_API_KEY"):
        interpreter.offline = False
        interpreter.llm.model = settings.openai_model
        interpreter.auto_run = True
        interpreter.system_message = (
            "You are an autonomous agent capable of controlling the mouse, keyboard, and "
            "browser to complete tasks. Use your vision capabilities to analyze the screen "
            "before clicking."
        )
        return

    # Fall back to local Ollama.
    interpreter.offline = True
    interpreter.llm.model = settings.ollama_model
    interpreter.llm.api_base = settings.ollama_base
    interpreter.auto_run = True
    interpreter.system_message = (
        "You are an autonomous agent capable of controlling the mouse, keyboard, and "
        "browser to complete tasks. Use your vision capabilities to analyze the screen "
        "before clicking."
    )


def switch_to_small_ollama(settings: Settings) -> str | None:
    models = _get_ollama_models(settings.ollama_base)
    picked = _pick_small_ollama_model(models)
    if not picked:
        return None
    interpreter.offline = True
    interpreter.llm.model = f"ollama/{picked}"
    interpreter.llm.api_base = settings.ollama_base
    return picked

    # NOTE: Do not overwrite interpreter.computer with a bool.
    # Some versions expect a Computer object; setting to True breaks .terminal access.
