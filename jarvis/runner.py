from __future__ import annotations

import json
import logging
import os
import socketserver
import urllib.request
from dataclasses import dataclass
from typing import List

from .actions import configure_interpreter, switch_to_small_ollama
from .config import Settings
from .logger import setup_logging
from .memory import MemoryStore
from .ollama import ensure_ollama_running
from .packs import PACKS

try:
    with open("C:/Users/codym/MyAgent/data/runner_loaded.txt", "w", encoding="utf-8") as handle:
        handle.write(__file__)
except Exception:
    pass

@dataclass
class Runner:
    settings: Settings
    memory: MemoryStore

    def _get_mode(self) -> str:
        return self.memory.get("mode") or "general"

    def _set_mode(self, mode: str) -> None:
        self.memory.set("mode", mode)

    def _get_active_packs(self) -> List[str]:
        raw = self.memory.get("active_packs")
        if not raw:
            return []
        try:
            return json.loads(raw)
        except Exception:
            return []

    def _set_active_packs(self, packs: List[str]) -> None:
        self.memory.set("active_packs", json.dumps(packs))

    def _mode_prefix(self, mode: str) -> str:
        if mode == "prompt_builder":
            return (
                "You are a Prompt Builder. Ask 2-3 clarifying questions first. "
                "Then produce a final, high-quality prompt with sections: "
                "Revised Prompt, Suggestions, Questions. Be concise.\n"
            )
        if mode == "legal_research":
            return (
                "You are a legal research assistant. Provide a clear, structured answer, "
                "flag any uncertainty, and include source-citation placeholders like [source]. "
                "Add a brief disclaimer: 'Not legal advice.'\n"
            )
        if mode == "agentic_uiux":
            return (
                "You are an agentic product builder. Respond with three sections: "
                "Planner (goal + steps), Builder (implementation), Reviewer (risks/tests). "
                "Emphasize UX clarity, accessibility, and consistency.\n"
            )
        return ""

    def _pack_context(self, active: List[str]) -> str:
        if not active:
            return ""
        blocks = []
        for name in active:
            content = PACKS.get(name)
            if content:
                blocks.append(f"[PACK:{name}]\n{content}\n")
        return "\n".join(blocks)

    def handle_command(self, command: str) -> str:
        logging.info("command: %s", command)
        self.memory.log_event("command", command)

        cmd = command.strip().lower()
        if cmd == "ping":
            return "ok"
        if cmd == "info":
            payload = {
                "mode": self._get_mode(),
                "active_packs": self._get_active_packs(),
                "available_packs": sorted(PACKS.keys()),
                "use_openai": os.getenv("JARVIS_USE_OPENAI", "0") == "1",
            }
            return json.dumps(payload)
        if command.startswith("/openai "):
            flag = command.split(" ", 1)[1].strip().lower()
            if flag in ("on", "true", "1"):
                os.environ["JARVIS_USE_OPENAI"] = "1"
                return "openai enabled"
            os.environ["JARVIS_USE_OPENAI"] = "0"
            return "openai disabled"

        if command.startswith("/mode "):
            mode = command.split(" ", 1)[1].strip()
            self._set_mode(mode)
            return f"mode set: {mode}"

        if command.startswith("/pack "):
            parts = command.split(" ", 2)
            if len(parts) == 2 and parts[1] == "list":
                return "packs: " + ", ".join(sorted(PACKS.keys()))
            if len(parts) >= 3 and parts[1] == "add":
                name = parts[2].strip()
                if name not in PACKS:
                    return f"unknown pack: {name}"
                active = self._get_active_packs()
                if name not in active:
                    active.append(name)
                    self._set_active_packs(active)
                return f"pack added: {name}"
            if len(parts) >= 3 and parts[1] == "remove":
                name = parts[2].strip()
                active = [p for p in self._get_active_packs() if p != name]
                self._set_active_packs(active)
                return f"pack removed: {name}"
            if len(parts) >= 3 and parts[1] == "show":
                name = parts[2].strip()
                content = PACKS.get(name)
                return content or f"unknown pack: {name}"
            if len(parts) == 2 and parts[1] == "clear":
                self._set_active_packs([])
                return "packs cleared"
            return "pack commands: /pack list | /pack add <name> | /pack remove <name> | /pack show <name> | /pack clear"

        backend = os.getenv("JARVIS_BACKEND", "ollama").strip().lower()

        if backend in ("ollama", "local", "llm"):
            reply = self._ollama_generate(command)
            return reply or "ok"

        try:
            from interpreter import interpreter
            try:
                import builtins
                builtins.display_markdown_message = lambda *args, **kwargs: None
                import interpreter.core.respond as respond_mod
                respond_mod.display_markdown_message = lambda *args, **kwargs: None
            except Exception:
                pass

            mode = self._get_mode()
            active = self._get_active_packs()
            prefix = self._mode_prefix(mode)
            pack_ctx = self._pack_context(active)
            payload = f"{pack_ctx}{prefix}{command}"
            interpreter.chat(payload, display=False)
            return "ok"
        except Exception as exc:
            # If OpenAI quota is exceeded, fall back to a small local Ollama model if available.
            err = str(exc)
            if "quota" in err.lower() or "RateLimitError" in err:
                picked = switch_to_small_ollama(self.settings)
                if picked:
                    try:
                        from interpreter import interpreter

                        mode = self._get_mode()
                        active = self._get_active_packs()
                        prefix = self._mode_prefix(mode)
                        pack_ctx = self._pack_context(active)
                        payload = f"{pack_ctx}{prefix}{command}"
                        interpreter.chat(payload, display=False)
                        return f"ok (fallback:{picked})"
                    except Exception as exc2:
                        logging.exception("command_failed_fallback")
                        return f"error: {exc2}"
            logging.exception("command_failed")
            return f"error: {exc}"

    def _ollama_generate(self, prompt: str) -> str:
        model = os.getenv("JARVIS_OLLAMA_CHAT_MODEL", "gemma:2b")
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        data = json.dumps(payload).encode("utf-8")
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:11434/api/generate",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")
            out = json.loads(raw)
            return out.get("response", "").strip()
        except Exception as exc:
            return f"error: {exc}"


class _TCPHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        data = self.rfile.readline().decode("utf-8", errors="ignore").strip()
        if not data:
            return
        result = self.server.runner.handle_command(data)
        self.wfile.write((result + "\n").encode("utf-8"))


class JarvisServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

    def __init__(self, host: str, port: int, runner: Runner) -> None:
        super().__init__((host, port), _TCPHandler)
        self.runner = runner


def serve(settings: Settings) -> None:
    setup_logging(settings.log_file)
    ensure_ollama_running()
    configure_interpreter(settings)

    memory = MemoryStore(settings.memory_db)
    runner = Runner(settings=settings, memory=memory)

    logging.info("jarvis server starting on %s:%s", settings.server_host, settings.server_port)
    server = JarvisServer(settings.server_host, settings.server_port, runner)
    with server:
        server.serve_forever()


def run_interactive(settings: Settings) -> None:
    setup_logging(settings.log_file)
    ensure_ollama_running()
    configure_interpreter(settings)

    memory = MemoryStore(settings.memory_db)
    runner = Runner(settings=settings, memory=memory)

    logging.info("jarvis interactive started")
    while True:
        try:
            command = input("Command: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            return
        if not command:
            continue
        runner.handle_command(command)
