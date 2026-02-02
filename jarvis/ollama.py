from __future__ import annotations

import socket
import subprocess
import time


def is_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        try:
            sock.connect((host, port))
            return True
        except OSError:
            return False


def ensure_ollama_running(host: str = "127.0.0.1", port: int = 11434) -> None:
    if is_port_open(host, port):
        return

    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    except Exception:
        return

    for _ in range(20):
        if is_port_open(host, port):
            return
        time.sleep(0.25)
