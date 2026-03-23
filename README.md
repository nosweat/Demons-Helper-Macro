# ⌨ Demons Helper

A lightweight macro tool for automating key sequences — built for games using DirectInput (works where regular key simulation fails).

---

## Features

- Up to 20 configurable key slots with per-key cooldown delays
- Click-to-capture key binding (no manual typing)
- Global hotkey toggle — works even when the window is not focused
- Loop or single-run mode
- Persistent config via `macro_config.json`
- DirectInput key simulation via `pydirectinput` (game compatible)

---

## Prerequisites

### Python
- Python **3.8 or higher** — https://www.python.org/downloads/
- Make sure to check **"Add Python to PATH"** during installation

### Dependencies

Install all required packages via pip:

```bash
pip install pynput pydirectinput
```

| Package | Purpose |
|---|---|
| `pynput` | Listening for the global hotkey |
| `pydirectinput` | Sending keystrokes via DirectInput scancodes |
| `tkinter` | UI — bundled with Python, no install needed |

## Notes

- Config is auto-saved to `macro_config.json` in the same directory as the script/exe
- The macro uses **DirectInput scancodes** — it should work in most games that block standard key simulation
- Run as **Administrator** if keystrokes are not being received by the target application
