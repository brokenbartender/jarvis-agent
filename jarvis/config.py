from __future__ import annotations

import os
from dataclasses import dataclass


def _load_dotenv() -> None:
    env_path = os.getenv("JARVIS_ENV_FILE")
    if not env_path:
        env_path = os.path.join(os.getcwd(), ".env")
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip().lstrip("\ufeff")
                value = value.strip()
                if key and key not in os.environ:
                    os.environ[key] = value
    except Exception:
        return


def _env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value is not None and value != "" else default


@dataclass
class Settings:
    data_dir: str = _env("JARVIS_DATA_DIR", os.path.join(os.getcwd(), "data"))
    memory_db: str = _env("JARVIS_MEMORY_DB", os.path.join(os.getcwd(), "data", "memory.db"))
    log_file: str = _env("JARVIS_LOG_FILE", os.path.join(os.getcwd(), "data", "jarvis.log"))
    ollama_base: str = _env("JARVIS_OLLAMA_BASE", "http://localhost:11434")
    ollama_model: str = _env("JARVIS_OLLAMA_MODEL", "ollama/llama3.2-vision")
    openai_model: str = _env("JARVIS_OPENAI_MODEL", "gpt-4o")
    server_host: str = _env("JARVIS_SERVER_HOST", "127.0.0.1")
    server_port: int = int(_env("JARVIS_SERVER_PORT", "8123"))


def get_settings() -> Settings:
    _load_dotenv()
    return Settings()
