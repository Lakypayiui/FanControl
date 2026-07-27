#!/usr/bin/env python3
"""
Fan Control — Icono nativo en la barra de menú + ventana moderna
"""
import os
import subprocess
import sys
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox

import rumps

HELPER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "helper/smc-helper")
REFRESH_INTERVAL_MS = 2000
SLIDER_COOLDOWN_SEC = 4.0

BG       = "#1e1e2e"
CARD_BG  = "#2a2a3c"
ACCENT   = "#89b4fa"
TEXT     = "#cdd6f4"
TEXT_DIM = "#a6adc8"

def run_helper(args):
    result = subprocess.run(
        [HELPER_PATH] + [str(a) for a in args],
        capture_output=True, text=True
    )
    return result.returncode, result.stdout, result.stderr

def parse_info(output):
    fans, temps = [], {"cpu": None, "gpu": None}
    for line in output.splitlines():
        if line.startswith("TEMP_CPU="):
            try: temps["cpu"] = float(line.split("=", 1)[1])
            except: pass
        elif line.startswith("TEMP_GPU="):
            try: temps["gpu"] = float(line.split("=", 1)[1])
            except: pass
        elif line.startswith("FAN="):
            parts = dict(t.split("=", 1) for t in line.split())
            fans.append({
                "index": int(parts["FAN"]),
                "actual": float(parts["ACTUAL"]),
                "min": float(parts["MIN"]),
                "max": float(parts["MAX"]),
                "target": float(parts["TARGET"]),
                "mode": parts["MODE"],
            })
    return fans, temps

class FanCard(ttk.Frame):
    def __init__(self, parent, fan_index, min_rpm, max_rpm, on_set):
        super().__init__(parent, style="Card.TFrame", padding=14)
        self.fan_index = fan_index
        self.on_set = on_set
        self.min_rpm = min_rpm
        self.max_rpm = max_rpm
        self._last_user_move = 0.0

        ttk.Label(self, text=f"Ventilador {fan_index}", style="Title.TLabel").pack(anchor="w")
        self.status_var = tk.StringVar(value="—")
        ttk.Label(self, textvariable=self.status_var, style="Dim.TLabel").pack(anchor="w", pady=(2, 8))

        row = ttk.Frame(self, style="Card.TFrame")
        row.pack(fill="x")

        self.slider_var = tk.DoubleVar(value=min_rpm)
        self.slider = ttk.Scale(row, from_=min_rpm, to=max_rpm,
                                variable=self.slider_var, orient="horizontal",
                                command=self._on_move, length=240)
        self.slider.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.value_label = ttk.Label(row, text=f"{int(min_rpm)}", style="Value.TLabel", width=5)
        self.value_label.pack(side="left")

        ttk.Button(self, text="Aplicar", command=self._apply, style="Accent.TButton").pack(anchor="w", pady=(10, 0))

    def _on_move(self, v):
        self._last_user_move = time.time()
        self.value_label.config(text=f"{int(float(v))}")

    def _apply(self):
        self.on_set(self.fan_index, int(self.slider_var.get()))

    def update_status(self, fan):
        estado = "Manual" if fan["mode"] == "MANUAL" else "Automático"
        self.status_var.set(f"{int(fan['actual']):,} RPM  ·  {estado}")

        if time.time() - self._last_user_move > SLIDER_COOLDOWN_SEC:
            val = max(self.min_rpm, min(self.max_rpm, fan["actual"]))
            self.slider_var.set(val)
            self.value_label.config(text=f"{int(val)}")

class ControlWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Control de Ventiladores")
        self.geometry("460x580")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.withdraw)

        self._setup_styles()

        # Header + temps
        top = ttk.Frame(self, style="Main.TFrame")
        top.pack(fill="x", padx=18, pady=(16, 10))

        ttk.Label(top, text="Ventiladores", style="Header.TLabel").pack(anchor="w")

        temp_row = ttk.Frame(self, style="Main.TFrame")
        temp_row.pack(fill="x", padx=18, pady=(0, 12))

        self.cpu_var = tk.StringVar(value="—")
        self.gpu_var = tk.StringVar(value="—")

        for label, var in [("CPU", self.cpu_var), ("GPU", self.gpu_var)]:
            card = ttk.Frame(temp_row, style="Temp.TFrame", padding=12)
            card.pack(side="left", fill="x", expand=True, padx=(0, 8) if label == "CPU" else 0)
            ttk.Label(card, text=label, style="Dim.TLabel").pack(anchor="w")
            ttk.Label(card, textvariable=var, style="Temp.TLabel").pack(anchor="w")

        self.rows_container = ttk.Frame(self, style="Main.TFrame")
        self.rows_container.pack(fill="both", expand=True, padx=18)
        self.rows = {}

        bottom = ttk.Frame(self, style="Main.TFrame", padding=(18, 12))
        bottom.pack(fill="x", side="bottom")
        ttk.Button(bottom, text="Modo automático", command=self.set_auto, style="Accent.TButton").pack(side="left")
        ttk.Button(bottom, text="Actualizar", command=self.refresh).pack(side="right")

        self.refresh()
        self.after(REFRESH_INTERVAL_MS, self._loop)

    def _setup_styles(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("Main.TFrame", background=BG)
        s.configure("Card.TFrame", background=CARD_BG)
        s.configure("Temp.TFrame", background=CARD_BG)
        s.configure("Header.TLabel", background=BG, foreground=TEXT, font=("SF Pro Display", 17, "bold"))
        s.configure("Title.TLabel", background=CARD_BG, foreground=TEXT, font=("SF Pro Display", 12, "bold"))
        s.configure("Dim.TLabel", background=CARD_BG, foreground=TEXT_DIM, font=("SF Pro Text", 11))
        s.configure("Value.TLabel", background=CARD_BG, foreground=ACCENT, font=("SF Pro Display", 12, "bold"))
        s.configure("Temp.TLabel", background=CARD_BG, foreground=TEXT, font=("SF Pro Display", 22, "bold"))
        s.configure("TButton", background=CARD_BG, foreground=TEXT, font=("SF Pro Text", 11), padding=8)
        s.map("TButton", background=[("active", "#3a3a4c")])
        s.configure("Accent.TButton", background=ACCENT, foreground="#1e1e2e", font=("SF Pro Text", 11, "bold"), padding=8)
        s.map("Accent.TButton", background=[("active", "#74c7ec")])
        s.configure("Horizontal.TScale", background=CARD_BG, troughcolor="#3a3a4c")

    def _loop(self):
        if self.winfo_exists():
            self.refresh()
            self.after(REFRESH_INTERVAL_MS, self._loop)

    def refresh(self):
        code, out, _ = run_helper(["info"])
        if code != 0:
            return
        fans, temps = parse_info(out)

        if temps["cpu"] is not None:
            self.cpu_var.set(f"{temps['cpu']:.1f} °C")
        if temps["gpu"] is not None:
            self.gpu_var.set(f"{temps['gpu']:.1f} °C")

        for fan in fans:
            idx = fan["index"]
            if idx not in self.rows:
                mn = fan["min"] if fan["min"] < fan["max"] else 2000
                mx = fan["max"] if fan["max"] > fan["min"] else 7000
                card = FanCard(self.rows_container, idx, mn, mx, self.set_speed)
                card.pack(fill="x", pady=5)
                self.rows[idx] = card
            self.rows[idx].update_status(fan)

    def set_speed(self, idx, rpm):
        code, _, err = run_helper(["set", idx, rpm])
        if code != 0:
            messagebox.showerror("Error", err)
        self.refresh()

    def set_auto(self):
        run_helper(["auto"])
        self.refresh()

class FanApp(rumps.App):
    def __init__(self):
        super().__init__("🌀", quit_button=None)

        self.menu = [
            rumps.MenuItem("Abrir panel de control", callback=self.show_panel),
            rumps.MenuItem("Modo automático", callback=self.do_auto),
            None,
            rumps.MenuItem("Salir", callback=rumps.quit_application),
        ]

        # Tk root oculto
        self.tk_root = tk.Tk()
        self.tk_root.withdraw()

        self.panel = ControlWindow(self.tk_root)
        self.panel.withdraw()

        # Actualizar título del icono periódicamente
        rumps.Timer(self.update_title, 3).start()

    def update_title(self, _):
        code, out, _ = run_helper(["info"])
        if code == 0:
            fans, _ = parse_info(out)
            if fans:
                avg = sum(f["actual"] for f in fans) / len(fans)
                self.title = f"🌀 {int(avg)}"

    def show_panel(self, _=None):
        self.panel.deiconify()
        self.panel.lift()
        self.panel.focus_force()

    def do_auto(self, _=None):
        run_helper(["auto"])
        self.panel.refresh()

if __name__ == "__main__":
    if not os.path.exists(HELPER_PATH):
        print("No se encontró smc-helper")
        sys.exit(1)

    st = os.stat(HELPER_PATH)
    if not (st.st_mode & 0o4000) or st.st_uid != 0:
        print("El helper no es setuid. Ejecuta:")
        print(f"  sudo chown root:wheel {HELPER_PATH}")
        print(f"  sudo chmod 4755 {HELPER_PATH}")
        sys.exit(1)

    FanApp().run()