from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from jarvis.config import get_settings

FAVICON_SVG = b"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>
  <rect width='64' height='64' rx='14' fill='#0b0f15'/>
  <path d='M16 10h32l6 12v20l-8 12H18L10 42V22z' fill='#d8a431' stroke='#a06e14' stroke-width='2'/>
  <path d='M10 22l12-4v30l-10-2z' fill='#a81e1e'/>
  <path d='M54 22l-12-4v30l10-2z' fill='#a81e1e'/>
  <path d='M22 20h20l-2 6H24z' fill='#9b6a16'/>
  <path d='M22 30h10l-2 4H20z' fill='#1fdcdc'/>
  <path d='M42 30H32l2 4h10z' fill='#1fdcdc'/>
  <path d='M26 42h12l-2 4H28z' fill='#8a5c12'/>
</svg>"""

HTML = r"""
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Jarvis Console</title>
    <link rel="icon" href="/favicon.ico" />
    <style>
      :root {
        --bg: #0c0f14;
        --panel: #121723;
        --panel-2: #0f141f;
        --text: #e7ebf2;
        --muted: #9aa3b2;
        --accent: #4ea3ff;
        --accent-2: #68e3a6;
        --danger: #ff6b6b;
        --border: #1f2a3a;
        --shadow: 0 20px 40px rgba(0,0,0,.35);
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: "Segoe UI", "Inter", system-ui, -apple-system, sans-serif;
        background: radial-gradient(1200px 600px at 10% -20%, #1b2440 0%, transparent 60%),
                    radial-gradient(800px 400px at 90% 0%, #102438 0%, transparent 60%),
                    var(--bg);
        color: var(--text);
      }
      .app {
        display: grid;
        grid-template-columns: 280px 1fr;
        height: 100vh;
      }
      .sidebar {
        border-right: 1px solid var(--border);
        background: linear-gradient(180deg, #101622, #0c1018);
        padding: 24px 18px;
      }
      .brand {
        display: flex;
        align-items: center;
        gap: 10px;
        font-weight: 700;
        letter-spacing: .5px;
      }
      .brand .dot {
        width: 10px; height: 10px; border-radius: 50%;
        background: var(--accent-2);
        box-shadow: 0 0 10px var(--accent-2);
      }
      .section {
        margin-top: 24px;
        font-size: 12px;
        text-transform: uppercase;
        color: var(--muted);
        letter-spacing: 1px;
      }
      .item {
        margin-top: 10px;
        padding: 10px 12px;
        border-radius: 10px;
        background: var(--panel-2);
        border: 1px solid var(--border);
        color: var(--text);
        font-size: 13px;
      }
      .main {
        display: grid;
        grid-template-rows: auto 1fr auto;
        height: 100vh;
      }
      .topbar {
        padding: 20px 28px;
        border-bottom: 1px solid var(--border);
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: rgba(10,14,20,.6);
        backdrop-filter: blur(8px);
      }
      .status {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-size: 12px;
        color: var(--muted);
      }
      .status .pill {
        padding: 4px 10px;
        border-radius: 999px;
        background: #111a28;
        border: 1px solid var(--border);
        color: var(--accent-2);
      }
      .chat {
        padding: 28px;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        gap: 14px;
      }
      .bubble {
        max-width: 72ch;
        padding: 14px 16px;
        border-radius: 16px;
        background: var(--panel);
        border: 1px solid var(--border);
        box-shadow: var(--shadow);
        line-height: 1.45;
        white-space: pre-wrap;
      }
      .bubble.user {
        align-self: flex-end;
        background: linear-gradient(180deg, #1a2840, #141f33);
        border-color: #24344c;
      }
      .bubble.jarvis {
        align-self: flex-start;
      }
      .composer {
        padding: 18px 28px;
        border-top: 1px solid var(--border);
        background: rgba(12,16,23,.8);
        display: flex;
        gap: 12px;
      }
      textarea {
        flex: 1;
        background: #0f1522;
        color: var(--text);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 12px 14px;
        font-size: 14px;
        min-height: 52px;
        resize: vertical;
      }
      button {
        background: linear-gradient(180deg, #2b6fda, #1f5bb8);
        color: white;
        border: none;
        padding: 12px 18px;
        border-radius: 12px;
        font-weight: 600;
        cursor: pointer;
      }
      button.secondary {
        background: #151d2b;
        border: 1px solid var(--border);
        color: var(--muted);
      }
      .hint {
        font-size: 12px;
        color: var(--muted);
      }
      .banner {
        margin: 14px 28px 0 28px;
        padding: 10px 14px;
        border-radius: 12px;
        border: 1px solid #3a1d1d;
        background: #241212;
        color: #ffb3b3;
        display: none;
      }
      @media (max-width: 980px) {
        .app { grid-template-columns: 1fr; }
        .sidebar { display: none; }
      }
    </style>
  </head>
  <body>
    <div class="app">
      <aside class="sidebar">
        <div class="brand"><span class="dot"></span> JARVIS</div>
        <div class="section">Status</div>
        <div class="item" id="statusBox">Disconnected</div>
        <div class="section">Modes</div>
        <div class="item">
          <button class="secondary" onclick="setMode('general')">General</button>
          <button class="secondary" onclick="setMode('prompt_builder')">Prompt Builder</button>
          <button class="secondary" onclick="setMode('legal_research')">Legal Research</button>
          <button class="secondary" onclick="setMode('agentic_uiux')">Agentic UI/UX</button>
        </div>
        <div class="section">Brain</div>
        <div class="item">
          <button class="secondary" onclick="toggleOpenAI()">Toggle OpenAI</button>
          <div class="hint">Uses OpenAI Responses API when enabled.</div>
        </div>
        <div class="section">Streaming</div>
        <div class="item">
          <button class="secondary" onclick="toggleStream()">Toggle Stream</button>
          <div class="hint">Stream local Ollama output.</div>
        </div>
        <div class="section">Knowledge Packs</div>
        <div class="item">
          <button class="secondary" onclick="togglePack('legal_ai_toolkit')">Legal Toolkit</button>
          <button class="secondary" onclick="togglePack('legal_prompting')">Legal Prompts</button>
          <button class="secondary" onclick="togglePack('legal_compliance')">Compliance</button>
          <button class="secondary" onclick="togglePack('legal_workflows')">Legal Workflows</button>
          <button class="secondary" onclick="togglePack('legal_efficiency_apps')">Efficiency Apps</button>
          <button class="secondary" onclick="togglePack('ai_selfhood_risks')">AI Selfhood</button>
          <button class="secondary" onclick="togglePack('agentic_uiux')">Agentic UI/UX</button>
        </div>
        <div class="section">Active</div>
        <div class="item" id="activeState">Mode: general<br/>Packs: none</div>
      </aside>
      <main class="main">
        <div class="topbar">
          <div>
            <div style="font-size:18px;font-weight:700;">Jarvis Console</div>
            <div class="hint">Your autonomous developer assistant</div>
          </div>
          <div class="status">
            <span class="pill" id="statusPill">offline</span>
          </div>
        </div>
        <div class="banner" id="offlineBanner">Backend offline. Starting Jarvis…</div>
        <div class="chat" id="chat"></div>
        <div class="composer">
          <textarea id="input" placeholder="Tell Jarvis what to do..."></textarea>
          <button id="send">Send</button>
          <button class="secondary" id="stop">Stop</button>
        </div>
      </main>
    </div>
    <script>
      const chat = document.getElementById('chat');
      const input = document.getElementById('input');
      const sendBtn = document.getElementById('send');
      const stopBtn = document.getElementById('stop');
      const statusPill = document.getElementById('statusPill');
      const statusBox = document.getElementById('statusBox');
      const offlineBanner = document.getElementById('offlineBanner');
      const activeState = document.getElementById('activeState');
      let activePacks = [];
      let activeMode = 'general';
      let useOpenAI = false;
      let useStream = true;

      function addBubble(text, who) {
        const el = document.createElement('div');
        el.className = `bubble ${who}`;
        el.textContent = text;
        chat.appendChild(el);
        chat.scrollTop = chat.scrollHeight;
      }

      async function ping() {
        try {
          const res = await fetch('/api/status');
          if (!res.ok) throw new Error();
          const data = await res.json();
          statusPill.textContent = data.status;
          statusBox.textContent = data.status === 'online' ? 'Connected' : 'Disconnected';
          offlineBanner.style.display = data.status === 'online' ? 'none' : 'block';
          if (data.mode) activeMode = data.mode;
          if (data.active_packs) activePacks = data.active_packs;
          if (data.use_openai !== undefined) useOpenAI = data.use_openai;
          activeState.innerHTML = `Mode: ${activeMode}<br/>Packs: ${activePacks.length ? activePacks.join(', ') : 'none'}`;
        } catch {
          statusPill.textContent = 'offline';
          statusBox.textContent = 'Disconnected';
          offlineBanner.style.display = 'block';
        }
      }

      async function sendMessage() {
        const msg = input.value.trim();
        if (!msg) return;
        addBubble(msg, 'user');
        input.value = '';
        if (useStream) {
          streamMessage(msg);
          return;
        }
        try {
          const res = await fetch('/api/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg })
          });
          const data = await res.json();
          addBubble(data.reply || 'ok', 'jarvis');
        } catch (e) {
          addBubble('Error: unable to reach Jarvis backend.', 'jarvis');
        }
      }

      sendBtn.addEventListener('click', sendMessage);
      input.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
          sendMessage();
        }
      });

      stopBtn.addEventListener('click', () => {
        addBubble('Stop requested (manual intervention needed).', 'jarvis');
      });

      function setMode(mode) {
        sendRaw(`/mode ${mode}`);
      }

      function togglePack(name) {
        const has = activePacks.includes(name);
        sendRaw(`/pack ${has ? 'remove' : 'add'} ${name}`);
      }

      function toggleOpenAI() {
        sendRaw(`/openai ${useOpenAI ? 'off' : 'on'}`);
      }

      function toggleStream() {
        useStream = !useStream;
        addBubble(`Streaming ${useStream ? 'enabled' : 'disabled'}.`, 'jarvis');
      }

      async function streamMessage(msg) {
        const bubble = document.createElement('div');
        bubble.className = 'bubble jarvis';
        bubble.textContent = '';
        chat.appendChild(bubble);
        chat.scrollTop = chat.scrollHeight;
        try {
          const res = await fetch('/api/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg })
          });
          const reader = res.body.getReader();
          const decoder = new TextDecoder();
          while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value);
            bubble.textContent += chunk;
            chat.scrollTop = chat.scrollHeight;
          }
        } catch (e) {
          bubble.textContent = 'Error: stream failed.';
        }
      }

      async function sendRaw(message) {
        try {
          await fetch('/api/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
          });
          ping();
        } catch (e) {
          addBubble('Error: unable to reach Jarvis backend.', 'jarvis');
        }
      }

      ping();
      setInterval(ping, 4000);
    </script>
  </body>
</html>
"""


def _send_command(host: str, port: int, message: str, timeout: float = 2.0) -> str:
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        sock.sendall((message + "\n").encode("utf-8"))
        return sock.recv(4096).decode("utf-8", errors="ignore").strip()


def _ensure_server_running() -> None:
    settings = get_settings()
    try:
        _send_command(settings.server_host, settings.server_port, "ping")
        return
    except Exception:
        subprocess.Popen(
            [sys.executable, "-m", "jarvis.cli", "serve", "--daemon"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        )


def _ollama_generate(prompt: str) -> str:
    model = os.getenv("JARVIS_OLLAMA_CHAT_MODEL", "gemma:2b")
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": 128},
    }
    data = json.dumps(payload).encode("utf-8")
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
        out = json.loads(raw)
        return out.get("response", "").strip()
    except Exception as exc:
        return f"error: {exc}"


class _Handler(BaseHTTPRequestHandler):
    def _json(self, data: dict, status: int = 200) -> None:
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/status":
            settings = get_settings()
            key_present = bool(os.getenv("OPENAI_API_KEY"))
            try:
                info_raw = _send_command(settings.server_host, settings.server_port, "info", timeout=2.0)
                info = json.loads(info_raw) if info_raw else {}
                info.update(
                    {
                        "status": "online",
                        "openai_key": key_present,
                        "server_host": settings.server_host,
                        "server_port": settings.server_port,
                    }
                )
                self._json(info)
            except Exception:
                self._json(
                    {
                        "status": "offline",
                        "openai_key": key_present,
                        "server_host": settings.server_host,
                        "server_port": settings.server_port,
                    }
                )
            return

        if path == "/favicon.ico":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "image/svg+xml")
            self.send_header("Content-Length", str(len(FAVICON_SVG)))
            self.end_headers()
            self.wfile.write(FAVICON_SVG)
            return

        if path == "/" or path == "/index.html":
            data = HTML.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/stream":
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            try:
                payload = json.loads(body.decode("utf-8"))
                message = payload.get("message", "").strip()
            except Exception:
                self._json({"reply": "invalid payload"}, status=400)
                return
            if not message:
                self._json({"reply": "empty message"}, status=400)
                return
            # Stream local Ollama output
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            reply = _ollama_generate(message)
            self.wfile.write(reply.encode("utf-8", errors="ignore"))
            return

        if path != "/api/send":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        try:
            payload = json.loads(body.decode("utf-8"))
            message = payload.get("message", "").strip()
        except Exception:
            self._json({"reply": "invalid payload"}, status=400)
            return

        if not message:
            self._json({"reply": "empty message"}, status=400)
            return

        settings = get_settings()
        direct_ui = os.getenv("JARVIS_UI_DIRECT", "1") == "1"
        if not direct_ui:
            try:
                reply = _send_command(settings.server_host, settings.server_port, message, timeout=120.0)
                self._json({"reply": reply or "ok"})
                return
            except Exception:
                _ensure_server_running()
                try:
                    reply = _send_command(settings.server_host, settings.server_port, message, timeout=120.0)
                    self._json({"reply": reply or "ok"})
                    return
                except Exception:
                    pass

        # Direct Ollama fallback (chat without backend)
        reply = _ollama_generate(message)
        self._json({"reply": reply or "ok"})

    def log_message(self, format: str, *args: object) -> None:
        return


def run_ui(host: str = "127.0.0.1", port: int = 8333) -> None:
    server = ThreadingHTTPServer((host, port), _Handler)
    server.serve_forever()
