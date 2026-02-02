from __future__ import annotations

import os
from typing import Any, Dict, List

try:
    import pyautogui
except Exception:  # pragma: no cover - optional at runtime
    pyautogui = None

try:
    import pygetwindow
except Exception:  # pragma: no cover - optional at runtime
    pygetwindow = None


def _require(module, name: str) -> None:
    if module is None:
        raise RuntimeError(f"{name} not installed")


def _configure_pyautogui() -> None:
    _require(pyautogui, "pyautogui")
    # Allow disabling failsafe via env for uninterrupted runs.
    if os.getenv("JARVIS_PYAUTOGUI_FAILSAFE", "1") == "0":
        pyautogui.FAILSAFE = False
    pyautogui.PAUSE = float(os.getenv("JARVIS_PYAUTOGUI_PAUSE", "0.05"))


def get_screen_size() -> Dict[str, int]:
    _configure_pyautogui()
    width, height = pyautogui.size()
    return {"width": int(width), "height": int(height)}


def mouse_move(x: int, y: int, duration: float = 0.0) -> str:
    _configure_pyautogui()
    pyautogui.moveTo(int(x), int(y), duration=float(duration))
    return "ok"


def mouse_click(x: int | None = None, y: int | None = None, button: str = "left", clicks: int = 1) -> str:
    _configure_pyautogui()
    if x is not None and y is not None:
        pyautogui.click(int(x), int(y), clicks=int(clicks), button=button)
    else:
        pyautogui.click(clicks=int(clicks), button=button)
    return "ok"


def mouse_drag(x: int, y: int, duration: float = 0.2, button: str = "left") -> str:
    _configure_pyautogui()
    pyautogui.dragTo(int(x), int(y), duration=float(duration), button=button)
    return "ok"


def scroll(amount: int) -> str:
    _configure_pyautogui()
    pyautogui.scroll(int(amount))
    return "ok"


def type_text(text: str, interval: float = 0.01) -> str:
    _configure_pyautogui()
    pyautogui.typewrite(text, interval=float(interval))
    return "ok"


def key_press(key: str) -> str:
    _configure_pyautogui()
    pyautogui.press(key)
    return "ok"


def hotkey(*keys: str) -> str:
    _configure_pyautogui()
    if not keys:
        return "error: no keys"
    pyautogui.hotkey(*keys)
    return "ok"


def list_windows() -> List[Dict[str, Any]]:
    _require(pygetwindow, "pygetwindow")
    windows = []
    for win in pygetwindow.getAllWindows():
        try:
            title = win.title
            if not title:
                continue
            windows.append(
                {
                    "title": title,
                    "left": int(win.left),
                    "top": int(win.top),
                    "width": int(win.width),
                    "height": int(win.height),
                    "is_active": bool(win.isActive),
                }
            )
        except Exception:
            continue
    return windows


def get_active_window() -> Dict[str, Any]:
    _require(pygetwindow, "pygetwindow")
    win = pygetwindow.getActiveWindow()
    if not win:
        return {}
    return {
        "title": win.title,
        "left": int(win.left),
        "top": int(win.top),
        "width": int(win.width),
        "height": int(win.height),
        "is_active": bool(win.isActive),
    }


def focus_window(title_contains: str) -> str:
    _require(pygetwindow, "pygetwindow")
    if not title_contains:
        return "error: empty title"
    title_lc = title_contains.lower()
    for win in pygetwindow.getAllWindows():
        if win.title and title_lc in win.title.lower():
            try:
                win.activate()
                return "ok"
            except Exception as exc:
                return f"error: {exc}"
    return "error: window not found"
