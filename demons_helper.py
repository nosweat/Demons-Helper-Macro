import tkinter as tk
from tkinter import messagebox
import threading
import time
import json
import sys
import os

# pynput only for LISTENING to the hotkey
from pynput import keyboard as pynput_keyboard

# pydirectinput for PRESSING keys (works in games via DirectInput scancodes)
import pydirectinput

# ─── Constants ────────────────────────────────────────────────────────────────
CONFIG_FILE = "macro_config.json"
DARK_BG     = "#0f0f13"
PANEL_BG    = "#1a1a24"
ACCENT      = "#7c5cfc"
ACCENT2     = "#c084fc"
GREEN       = "#22c55e"
RED         = "#ef4444"
TEXT        = "#e2e8f0"
MUTED       = "#64748b"
BORDER      = "#2d2d3d"

# ─── Special key name map for pydirectinput ───────────────────────────────────
SPECIAL_KEYS = {
    "space":     "space",
    "enter":     "enter",
    "return":    "enter",
    "tab":       "tab",
    "shift":     "shift",
    "ctrl":      "ctrl",
    "alt":       "alt",
    "backspace": "backspace",
    "delete":    "delete",
    "esc":       "escape",
    "escape":    "escape",
    "up":        "up",
    "down":      "down",
    "left":      "left",
    "right":     "right",
    "home":      "home",
    "end":       "end",
    "pageup":    "pageup",
    "pagedown":  "pagedown",
    "capslock":  "capslock",
    "caps_lock": "capslock",
    "f1":  "f1",  "f2":  "f2",  "f3":  "f3",  "f4":  "f4",
    "f5":  "f5",  "f6":  "f6",  "f7":  "f7",  "f8":  "f8",
    "f9":  "f9",  "f10": "f10", "f11": "f11", "f12": "f12",
}


def press_key(key_str):
    """Press a key using pydirectinput (DirectInput scancodes — works in games)."""
    k = key_str.strip().lower()
    if not k:
        return
    mapped = SPECIAL_KEYS.get(k, k)
    try:
        pydirectinput.press(mapped)
    except Exception:
        pass


# ─── Macro Engine ─────────────────────────────────────────────────────────────
class MacroEngine:
    def __init__(self):
        self.keys        = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "", "", "", "", "", "", "", "", "", "", ""]
        self.delays      = [0.1] * 20
        self.enabled     = False
        self.loop        = True
        self.hotkey      = "f8"
        self._thread     = None
        self._stop_event = threading.Event()
        self._listener   = None

    # def _run(self):
    #     while not self._stop_event.is_set():
    #         for i, key in enumerate(self.keys):
    #             if self._stop_event.is_set():
    #                 break
    #             if not key.strip():
    #                 continue
    #             press_key(key)
    #             delay = self.delays[i]
    #             end = time.time() + delay
    #             while time.time() < end:
    #                 if self._stop_event.is_set():
    #                     return
    #                 time.sleep(0.01)
    #         if not self.loop:
    #             self.enabled = False
    #             break
    def _run(self):
        # Track when each key was last pressed (or when the run started)
        last_pressed = [0.0] * len(self.keys)

        while not self._stop_event.is_set():
            now = time.time()
            for i, key in enumerate(self.keys):
                if self._stop_event.is_set():
                    return
                
                raw = key.strip()
                if not raw:
                    continue

                delay = self.delays[i]
                # Only press if enough time has passed since last press
                if now - last_pressed[i] >= delay:
                    press_key(key)
                    last_pressed[i] = now  # reset the timer for this key

            if not self.loop:
                self.enabled = False
                break

            time.sleep(0.01)  # tight loop polling — avoids hammering the CPU

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1)

    def toggle(self):
        self.enabled = not self.enabled
        if self.enabled:
            self.start()
        else:
            self.stop()

    def save(self):
        data = {
            "keys":   self.keys,
            "delays": self.delays,
            "loop":   self.loop,
            "hotkey": self.hotkey,
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def load(self):
        if not os.path.exists(CONFIG_FILE):
            return
        try:
            with open(CONFIG_FILE) as f:
                data = json.load(f)
            self.keys    = data.get("keys",   self.keys)
            self.delays  = data.get("delays", self.delays)
            self.loop    = data.get("loop",   self.loop)
            self.hotkey  = data.get("hotkey", self.hotkey)
        except Exception:
            pass


# ─── UI ───────────────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.iconbitmap(resource_path("demons_helper.ico"))
        self.engine = MacroEngine()
        self.engine.load()

        self.title("⌨  Demons Helper")
        self.resizable(False, False)
        self.configure(bg=DARK_BG)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self._start_hotkey_listener()
        self._refresh_status()

    def _build_ui(self):
        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=DARK_BG, pady=14)
        hdr.pack(fill="x", padx=20)

        tk.Label(hdr, text="DEMONS HELPER", font=("Courier New", 13, "bold"),
                 bg=DARK_BG, fg=ACCENT2).pack(side="left")

        self.status_dot = tk.Label(hdr, text="●", font=("Courier New", 18),
                                   bg=DARK_BG, fg=MUTED)
        self.status_dot.pack(side="right")        

        self._copyright_lbl = tk.Label(self,
                                  text=f"For Demons By Demons",
                                  font=("Courier New", 8), bg=DARK_BG, fg=MUTED)
        self._copyright_lbl.pack(pady=(0, 10))

        self.status_lbl = tk.Label(hdr, text="IDLE", font=("Courier New", 9, "bold"),
                                   bg=DARK_BG, fg=MUTED)
        self.status_lbl.pack(side="right", padx=(0, 4))

        # ── Key slots card ────────────────────────────────────────────────────
        # card = tk.Frame(self, bg=PANEL_BG, padx=18, pady=14,
        #                 highlightbackground=BORDER, highlightthickness=1)
        # card.pack(fill="x", padx=20, pady=(0, 10))

        # tk.Label(card, text="KEY SEQUENCE", font=("Courier New", 8, "bold"),
        #          bg=PANEL_BG, fg=MUTED).grid(row=0, column=0, columnspan=4,
        #          sticky="w", pady=(0, 8))

        # for col, h in enumerate(["SLOT", "KEY", "DELAY (s)", ""]):
        #     tk.Label(card, text=h, font=("Courier New", 7, "bold"),
        #              bg=PANEL_BG, fg=MUTED).grid(row=1, column=col,
        #              padx=(0, 10), sticky="w")

        # self.key_vars   = []
        # self.delay_vars = []

        # for i in range(20):
        #     row = i + 2

        #     tk.Label(card, text=f"{i+1}", font=("Courier New", 11, "bold"),
        #              bg=PANEL_BG, fg=ACCENT, width=3).grid(row=row, column=0,
        #              pady=4, sticky="w")

        #     kv = tk.StringVar(value=self.engine.keys[i])
        #     self.key_vars.append(kv)
        #     tk.Entry(card, textvariable=kv, width=8,
        #              font=("Courier New", 11),
        #              bg="#252535", fg=TEXT, insertbackground=ACCENT,
        #              relief="flat", bd=4,
        #              highlightbackground=BORDER, highlightthickness=1
        #              ).grid(row=row, column=1, padx=(0, 12))

        #     dv = tk.StringVar(value=str(self.engine.delays[i]))
        #     self.delay_vars.append(dv)
        #     tk.Entry(card, textvariable=dv, width=6,
        #              font=("Courier New", 11),
        #              bg="#252535", fg=TEXT, insertbackground=ACCENT,
        #              relief="flat", bd=4,
        #              highlightbackground=BORDER, highlightthickness=1
        #              ).grid(row=row, column=2, padx=(0, 12))

        #     tk.Button(card, text="✕", font=("Courier New", 9),
        #               bg=PANEL_BG, fg=MUTED, relief="flat", cursor="hand2",
        #               activebackground=PANEL_BG, activeforeground=RED,
        #               command=lambda v=kv: v.set("")
        #               ).grid(row=row, column=3)

        # ── Key slots card ────────────────────────────────────────────────────────────
        outer = tk.Frame(self, bg=PANEL_BG,
                        highlightbackground=BORDER, highlightthickness=1)
        outer.pack(fill="x", padx=20, pady=(0, 10))

        tk.Label(outer, text="KEY SEQUENCE", font=("Courier New", 8, "bold"),
                bg=PANEL_BG, fg=MUTED).grid(row=0, column=0, columnspan=4,
                sticky="w", padx=18, pady=(10, 4))

        for col, h in enumerate(["SLOT", "KEY", "DELAY (s)", ""]):
            tk.Label(outer, text=h, font=("Courier New", 7, "bold"),
                    bg=PANEL_BG, fg=MUTED).grid(row=1, column=col,
                    padx=(18 if col == 0 else 0, 10), sticky="w")

        # Scrollable canvas for slots
        canvas = tk.Canvas(outer, bg=PANEL_BG, highlightthickness=0,
                        height=10 * 36)  # 10 rows visible, each ~36px tall
        canvas.grid(row=2, column=0, columnspan=4, sticky="ew")

        scrollbar = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        scrollbar.grid(row=2, column=4, sticky="ns")
        canvas.configure(yscrollcommand=scrollbar.set)

        card = tk.Frame(canvas, bg=PANEL_BG)
        card_window = canvas.create_window((0, 0), window=card, anchor="nw")

        def _on_frame_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(e):
            canvas.itemconfig(card_window, width=e.width)

        card.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        # Mouse wheel scroll
        def _on_mousewheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self.key_vars   = []
        self.delay_vars = []

        # for i in range(20):
        #     row = i

        #     tk.Label(card, text=f"{i+1}", font=("Courier New", 11, "bold"),
        #             bg=PANEL_BG, fg=ACCENT, width=3).grid(row=row, column=0,
        #             pady=4, padx=(18, 0), sticky="w")

        #     kv = tk.StringVar(value=self.engine.keys[i])
        #     self.key_vars.append(kv)
        #     tk.Entry(card, textvariable=kv, width=8,
        #             font=("Courier New", 11),
        #             bg="#252535", fg=TEXT, insertbackground=ACCENT,
        #             relief="flat", bd=4,
        #             highlightbackground=BORDER, highlightthickness=1
        #             ).grid(row=row, column=1, padx=(0, 12))

        #     dv = tk.StringVar(value=str(self.engine.delays[i]))
        #     self.delay_vars.append(dv)
        #     tk.Entry(card, textvariable=dv, width=6,
        #             font=("Courier New", 11),
        #             bg="#252535", fg=TEXT, insertbackground=ACCENT,
        #             relief="flat", bd=4,
        #             highlightbackground=BORDER, highlightthickness=1
        #             ).grid(row=row, column=2, padx=(0, 12))

        #     tk.Button(card, text="✕", font=("Courier New", 9),
        #             bg=PANEL_BG, fg=MUTED, relief="flat", cursor="hand2",
        #             activebackground=PANEL_BG, activeforeground=RED,
        #             command=lambda v=kv: v.set("")
        #             ).grid(row=row, column=3)
        for i in range(20):
            row = i

            tk.Label(card, text=f"{i+1}", font=("Courier New", 11, "bold"),
                    bg=PANEL_BG, fg=ACCENT, width=3).grid(row=row, column=0,
                    pady=4, padx=(18, 0), sticky="w")

            kv = tk.StringVar(value=self.engine.keys[i])
            self.key_vars.append(kv)

            # ── Key capture button ────────────────────────────────────────────────
            def make_capture(var, idx):
                btn = tk.Button(card, textvariable=var, width=8,
                                font=("Courier New", 11),
                                bg="#252535", fg=ACCENT2,
                                relief="flat", bd=4, cursor="hand2",
                                highlightbackground=BORDER, highlightthickness=1,
                                activebackground="#252535", activeforeground=ACCENT)

                def on_click():
                    old = var.get()
                    var.set("...")
                    btn.config(fg=ACCENT)
                    btn.focus_set()

                    def on_key(e):
                        key_name = e.keysym.lower()
                        if key_name in ("shift_l", "shift_r", "control_l", "control_r",
                                        "alt_l", "alt_r", "super_l", "super_r", "caps_lock"):
                            return "break"
                        var.set(key_name)
                        btn.config(fg=ACCENT2)
                        btn.unbind("<KeyPress>")
                        btn.unbind("<FocusOut>")
                        return "break"  # ← prevent default button behaviour

                    def on_focus_out(e):
                        if var.get() == "...":
                            var.set(old)
                            btn.config(fg=ACCENT2)
                        btn.unbind("<KeyPress>")
                        btn.unbind("<FocusOut>")

                    btn.bind("<KeyPress>", on_key)
                    btn.bind("<FocusOut>", on_focus_out)

                btn.config(command=on_click)
                return btn

            make_capture(kv, i).grid(row=row, column=1, padx=(0, 12))

            dv = tk.StringVar(value=str(self.engine.delays[i]))
            self.delay_vars.append(dv)
            tk.Entry(card, textvariable=dv, width=6,
                    font=("Courier New", 11),
                    bg="#252535", fg=TEXT, insertbackground=ACCENT,
                    relief="flat", bd=4,
                    highlightbackground=BORDER, highlightthickness=1
                    ).grid(row=row, column=2, padx=(0, 12))

            tk.Button(card, text="✕", font=("Courier New", 9),
                    bg=PANEL_BG, fg=MUTED, relief="flat", cursor="hand2",
                    activebackground=PANEL_BG, activeforeground=RED,
                    command=lambda v=kv: v.set("")
                    ).grid(row=row, column=3)

        # ── Options card ──────────────────────────────────────────────────────
        opt = tk.Frame(self, bg=PANEL_BG, padx=18, pady=12,
                       highlightbackground=BORDER, highlightthickness=1)
        opt.pack(fill="x", padx=20, pady=(0, 10))

        tk.Label(opt, text="OPTIONS", font=("Courier New", 8, "bold"),
                 bg=PANEL_BG, fg=MUTED).grid(row=0, column=0, columnspan=4,
                 sticky="w", pady=(0, 8))

        tk.Label(opt, text="Loop", font=("Courier New", 10),
                 bg=PANEL_BG, fg=TEXT).grid(row=1, column=0, sticky="w", padx=(0, 8))

        self.loop_var = tk.BooleanVar(value=self.engine.loop)
        self._make_toggle(opt, self.loop_var).grid(row=1, column=1,
                                                    sticky="w", padx=(0, 24))

        tk.Label(opt, text="Toggle Hotkey", font=("Courier New", 10),
                 bg=PANEL_BG, fg=TEXT).grid(row=1, column=2, sticky="w", padx=(0, 8))

        self.hotkey_var = tk.StringVar(value=self.engine.hotkey)
        tk.Entry(opt, textvariable=self.hotkey_var, width=6,
                 font=("Courier New", 11, "bold"),
                 bg="#252535", fg=ACCENT2, insertbackground=ACCENT,
                 relief="flat", bd=4,
                 highlightbackground=BORDER, highlightthickness=1
                 ).grid(row=1, column=3, sticky="w")

        # self.hotkey_var = tk.StringVar(value=self.engine.hotkey)

        # def make_hotkey_capture(var):
        #     btn = tk.Button(opt, textvariable=var, width=6,
        #                     font=("Courier New", 11, "bold"),
        #                     bg="#252535", fg=ACCENT2,
        #                     relief="flat", bd=4, cursor="hand2",
        #                     highlightbackground=BORDER, highlightthickness=1,
        #                     activebackground="#252535", activeforeground=ACCENT)

        #     def on_click():
        #         old = var.get()
        #         var.set("...")
        #         btn.config(fg=ACCENT)
        #         btn.focus_set()

        #         def on_key(e):
        #             key_name = e.keysym.lower()
        #             if key_name in ("shift_l", "shift_r", "control_l", "control_r",
        #                             "alt_l", "alt_r", "super_l", "super_r", "caps_lock"):
        #                 return "break"
        #             var.set(key_name)
        #             btn.config(fg=ACCENT2)
        #             btn.unbind("<KeyPress>")
        #             btn.unbind("<FocusOut>")
        #             self.after(300, self._restart_hotkey_listener)
        #             return "break"

        #         def on_focus_out(e):
        #             if var.get() == "...":
        #                 var.set(old)
        #                 btn.config(fg=ACCENT2)
        #             btn.unbind("<KeyPress>")
        #             btn.unbind("<FocusOut>")

        #         btn.bind("<KeyPress>", on_key)
        #         btn.bind("<FocusOut>", on_focus_out)

        #     btn.config(command=on_click)
        #     return btn

        # make_hotkey_capture(self.hotkey_var).grid(row=1, column=3, sticky="w")

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_row = tk.Frame(self, bg=DARK_BG)
        btn_row.pack(fill="x", padx=20, pady=(0, 16))

        self.toggle_btn = tk.Button(
            btn_row, text="▶  START", font=("Courier New", 11, "bold"),
            bg=ACCENT, fg="white", relief="flat", cursor="hand2",
            activebackground=ACCENT2, activeforeground="white",
            padx=18, pady=8, command=self._toggle)
        self.toggle_btn.pack(side="left", padx=(0, 8))

        tk.Button(btn_row, text="💾  Save", font=("Courier New", 10),
                  bg=PANEL_BG, fg=TEXT, relief="flat", cursor="hand2",
                  activebackground=BORDER, activeforeground=ACCENT2,
                  padx=12, pady=8, command=self._save,
                  highlightbackground=BORDER, highlightthickness=1
                  ).pack(side="left", padx=(0, 8))

        tk.Button(btn_row, text="↺  Reset", font=("Courier New", 10),
                  bg=PANEL_BG, fg=TEXT, relief="flat", cursor="hand2",
                  activebackground=BORDER, activeforeground=RED,
                  padx=12, pady=8, command=self._reset,
                  highlightbackground=BORDER, highlightthickness=1
                  ).pack(side="left")

        # ── Footer hint ───────────────────────────────────────────────────────
        self._hint_lbl = tk.Label(self,
                                  text=f"Press  {self.engine.hotkey.upper()}  anywhere to toggle macro",
                                  font=("Courier New", 8), bg=DARK_BG, fg=MUTED)
        self._hint_lbl.pack(pady=(0, 10))

        self._thanks_lbl = tk.Label(self,
                                  text=f"special Thanks to @Solido,@Bliss,@Ouch",
                                  font=("Courier New", 8), bg=DARK_BG, fg=MUTED)
        self._thanks_lbl.pack(pady=(0, 10))        

    def _make_toggle(self, parent, var):
        frame = tk.Frame(parent, bg=PANEL_BG)
        btn = tk.Label(frame, font=("Courier New", 10, "bold"),
                       bg=PANEL_BG, cursor="hand2", padx=6, pady=2)

        def refresh(*_):
            if var.get():
                btn.config(text="ON ", fg=GREEN,
                           highlightbackground=GREEN, highlightthickness=1,
                           relief="solid")
            else:
                btn.config(text="OFF", fg=MUTED,
                           highlightbackground=BORDER, highlightthickness=1,
                           relief="solid")

        btn.bind("<Button-1>", lambda e: (var.set(not var.get()), refresh()))
        var.trace_add("write", refresh)
        refresh()
        btn.pack()
        return frame

    # ── Actions ───────────────────────────────────────────────────────────────
    # def _apply_config(self):
    #     for i in range(20):
    #         self.engine.keys[i] = self.key_vars[i].get()
    #         try:
    #             self.engine.delays[i] = float(self.delay_vars[i].get())
    #         except ValueError:
    #             self.engine.delays[i] = 0.1
    #     self.engine.loop   = self.loop_var.get()
    #     self.engine.hotkey = self.hotkey_var.get().strip().lower() or "f8"
    def _apply_config(self):
        TKINTER_KEY_MAP = {
            "return":   "enter",
            "prior":    "pageup",
            "next":     "pagedown",
            "delete":   "delete",
            "insert":   "insert",
            "backtick": "grave",
        }
        for i in range(20):
            raw = self.key_vars[i].get().strip().lower()
            self.engine.keys[i] = TKINTER_KEY_MAP.get(raw, raw)
            try:
                self.engine.delays[i] = float(self.delay_vars[i].get())
            except ValueError:
                self.engine.delays[i] = 0.1
        self.engine.loop   = self.loop_var.get()
        self.engine.hotkey = self.hotkey_var.get().strip().lower() or "f8"

    def _toggle(self):
        self._apply_config()
        self.engine.toggle()
        self._restart_hotkey_listener()

    def _save(self):
        self._apply_config()
        self.engine.save()
        self._show_toast("Config saved!")

    def _reset(self):
        if not messagebox.askyesno("Reset", "Reset all keys to defaults?"):
            return
        for i, k in enumerate(["1", "2", "3", "4", "5", "6", "7", "8", "9", "", "", "", "", "", "", "", "", "", "", ""]):
            self.key_vars[i].set(k)
            self.delay_vars[i].set("0.1")
        self.loop_var.set(True)
        self.hotkey_var.set("f8")

    def _refresh_status(self):
        if self.engine.enabled:
            self.status_dot.config(fg=GREEN)
            self.status_lbl.config(fg=GREEN, text="RUNNING")
            self.toggle_btn.config(text="⏹  STOP", bg=RED)
        else:
            self.status_dot.config(fg=MUTED)
            self.status_lbl.config(fg=MUTED, text="IDLE")
            self.toggle_btn.config(text="▶  START", bg=ACCENT)
        self._hint_lbl.config(
            text=f"Press  {self.engine.hotkey.upper()}  anywhere to toggle macro")
        self.after(300, self._refresh_status)

    def _show_toast(self, msg):
        toast = tk.Toplevel(self)
        toast.overrideredirect(True)
        toast.configure(bg=GREEN)
        tk.Label(toast, text=f"  {msg}  ", font=("Courier New", 10, "bold"),
                 bg=GREEN, fg="#0a0a0a", pady=6).pack()
        x = self.winfo_x() + self.winfo_width() // 2 - 60
        y = self.winfo_y() + self.winfo_height() - 50
        toast.geometry(f"+{x}+{y}")
        toast.after(1500, toast.destroy)

    # ── Global Hotkey Listener ────────────────────────────────────────────────
    def _start_hotkey_listener(self):
        hk = self.engine.hotkey.strip().lower()

        def on_press(key):
            try:
                name = key.name if hasattr(key, "name") else key.char
                if name and name.lower() == hk:
                    self._apply_config()   # ← already there ✓
                    self.engine.toggle()
            except Exception:
                pass

        self._listener = pynput_keyboard.Listener(on_press=on_press)
        self._listener.daemon = True
        self._listener.start()

    def _restart_hotkey_listener(self):
        if self._listener:
            self._listener.stop()
        self._start_hotkey_listener()

    def _on_close(self):
        self.engine.stop()
        if self._listener:
            self._listener.stop()
        self.destroy()

def resource_path(relative_path):
    """Get absolute path to resource — works for dev and PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()