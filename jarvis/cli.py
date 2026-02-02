from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import webbrowser

# Allow running as a script: python jarvis/cli.py ...
if __package__ is None or __package__ == "":
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from jarvis.config import get_settings
from jarvis.runner import run_interactive, serve
from jarvis.web import run_ui


def _send_command(host: str, port: int, message: str) -> str:
    with socket.create_connection((host, port), timeout=2.0) as sock:
        sock.sendall((message + "\n").encode("utf-8"))
        return sock.recv(4096).decode("utf-8", errors="ignore").strip()


def _spawn_detached(args: list[str]) -> None:
    subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="jarvis")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("run", help="Run interactive mode")

    serve_parser = sub.add_parser("serve", help="Run command server")
    serve_parser.add_argument("--daemon", action="store_true", help="Run in background")

    send_parser = sub.add_parser("send", help="Send a command to running server")
    send_parser.add_argument("message")

    ui_parser = sub.add_parser("ui", help="Run web UI")
    ui_parser.add_argument("--host", default="127.0.0.1")
    ui_parser.add_argument("--port", type=int, default=8333)
    ui_parser.add_argument("--open", action="store_true", help="Open browser")

    args = parser.parse_args()
    settings = get_settings()

    if args.cmd == "serve":
        if args.daemon:
            _spawn_detached([sys.executable, "-m", "jarvis.cli", "serve"])
            return
        serve(settings)
        return

    if args.cmd == "send":
        response = _send_command(settings.server_host, settings.server_port, args.message)
        print(response)
        return

    if args.cmd == "ui":
        if args.open:
            webbrowser.open(f"http://{args.host}:{args.port}")
        run_ui(args.host, args.port)
        return

    run_interactive(settings)


if __name__ == "__main__":
    main()
