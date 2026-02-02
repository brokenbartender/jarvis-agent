from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from openai import OpenAI


def _safe_path(path: str) -> Path:
    return Path(path).expanduser().resolve()


def list_files(path: str = ".", pattern: str = "*", limit: int = 200) -> list[str]:
    base = _safe_path(path)
    if not base.exists():
        return []
    results = [str(p) for p in base.rglob(pattern) if p.is_file()]
    return results[:limit]


def read_file(path: str, max_bytes: int = 200_000) -> str:
    target = _safe_path(path)
    if not target.exists():
        return ""
    data = target.read_bytes()
    return data[:max_bytes].decode("utf-8", errors="ignore")


def write_file(path: str, content: str) -> str:
    target = _safe_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return "ok"


def run_command(command: str, cwd: str | None = None, timeout: int = 120) -> str:
    if os.getenv("JARVIS_ALLOW_SHELL", "0") != "1":
        return "error: shell disabled (set JARVIS_ALLOW_SHELL=1)"
    result = subprocess.run(
        command,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return (result.stdout + "\n" + result.stderr).strip()


def screenshot(path: str = "data/screen.png") -> str:
    try:
        from PIL import ImageGrab

        target = _safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        img = ImageGrab.grab()
        img.save(target)
        return str(target)
    except Exception as exc:
        return f"error: {exc}"


TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "list_files",
        "description": "List files recursively under a path.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "pattern": {"type": "string"},
                "limit": {"type": "integer"},
            },
        },
        "strict": False,
    },
    {
        "type": "function",
        "name": "read_file",
        "description": "Read a text file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "max_bytes": {"type": "integer"},
            },
            "required": ["path"],
        },
        "strict": False,
    },
    {
        "type": "function",
        "name": "write_file",
        "description": "Write text to a file, creating folders if needed.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
        "strict": False,
    },
    {
        "type": "function",
        "name": "run_command",
        "description": "Run a shell command on the local machine.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "cwd": {"type": "string"},
                "timeout": {"type": "integer"},
            },
            "required": ["command"],
        },
        "strict": False,
    },
    {
        "type": "function",
        "name": "screenshot",
        "description": "Capture a screenshot to a file path.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
            },
        },
        "strict": False,
    },
]


_TOOL_MAP = {
    "list_files": list_files,
    "read_file": read_file,
    "write_file": write_file,
    "run_command": run_command,
    "screenshot": screenshot,
}


@dataclass
class OpenAIAgent:
    model: str = "gpt-4.1-2025-04-14"
    instructions: str = (
        "You are Jarvis, a world-class autonomous software engineer. "
        "Use tools when needed. Always verify changes before finalizing."
    )

    def __post_init__(self) -> None:
        self.client = OpenAI()

    def _call_tools(self, tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
        outputs = []
        for call in tool_calls:
            name = call.get("name")
            args_raw = call.get("arguments", "{}")
            try:
                args = json.loads(args_raw)
            except Exception:
                args = {}
            fn = _TOOL_MAP.get(name)
            result = f"error: unknown tool {name}"
            if fn:
                try:
                    result = fn(**args)
                except Exception as exc:
                    result = f"error: {exc}"
            outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": call.get("call_id"),
                    "output": json.dumps(result) if not isinstance(result, str) else result,
                }
            )
        return outputs

    def run(self, prompt: str) -> str:
        response = self.client.responses.create(
            model=self.model,
            instructions=self.instructions,
            input=[{"role": "user", "content": prompt}],
            tools=TOOLS,
            tool_choice="auto",
        )
        final_text = ""
        tool_calls: list[dict[str, Any]] = []
        for item in response.output:
            if item.get("type") == "message":
                for part in item.get("content", []):
                    if part.get("type") == "output_text":
                        final_text += part.get("text", "")
            if item.get("type") == "function_call":
                tool_calls.append(item)

        while tool_calls:
            tool_outputs = self._call_tools(tool_calls)
            response = self.client.responses.create(
                model=self.model,
                instructions=self.instructions,
                input=tool_outputs,
                previous_response_id=response.id,
                tools=TOOLS,
                tool_choice="auto",
            )
            tool_calls = []
            for item in response.output:
                if item.get("type") == "message":
                    for part in item.get("content", []):
                        if part.get("type") == "output_text":
                            final_text += part.get("text", "")
                if item.get("type") == "function_call":
                    tool_calls.append(item)

        return final_text.strip()

    def run_agentic(self, prompt: str) -> str:
        planner = "You are the Planner. Produce a concise step-by-step plan."
        builder = "You are the Builder. Execute the plan using tools."
        reviewer = "You are the Reviewer. Verify outputs and list risks/tests."

        plan = self._run_with_tools(prompt, planner)
        build = self._run_with_tools(f"Plan:\n{plan}\n\nTask:\n{prompt}", builder)
        review = self._run_with_tools(f"Plan:\n{plan}\n\nBuild Output:\n{build}", reviewer)
        return f"PLAN:\n{plan}\n\nBUILD:\n{build}\n\nREVIEW:\n{review}".strip()

    def _run_with_tools(self, prompt: str, instructions: str) -> str:
        response = self.client.responses.create(
            model=self.model,
            instructions=instructions,
            input=[{"role": "user", "content": prompt}],
            tools=TOOLS,
            tool_choice="auto",
        )
        final_text = ""
        tool_calls: list[dict[str, Any]] = []
        for item in response.output:
            if item.get("type") == "message":
                for part in item.get("content", []):
                    if part.get("type") == "output_text":
                        final_text += part.get("text", "")
            if item.get("type") == "function_call":
                tool_calls.append(item)

        while tool_calls:
            tool_outputs = self._call_tools(tool_calls)
            response = self.client.responses.create(
                model=self.model,
                instructions=instructions,
                input=tool_outputs,
                previous_response_id=response.id,
                tools=TOOLS,
                tool_choice="auto",
            )
            tool_calls = []
            for item in response.output:
                if item.get("type") == "message":
                    for part in item.get("content", []):
                        if part.get("type") == "output_text":
                            final_text += part.get("text", "")
                if item.get("type") == "function_call":
                    tool_calls.append(item)

        return final_text.strip()
