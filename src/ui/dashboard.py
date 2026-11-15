
import tkinter as tk
import math
import time

BG = "#070b12"
PANEL = "#101a27"
GREEN = "#8cffb5"
CYAN = "#55dfff"
WHITE = "#e7f2ff"
MUTED = "#71869b"

root = tk.Tk()
root.title("VICTOR | AI COMMAND CENTER")
root.configure(bg=BG)
root.state("zoomed")
root.minsize(1000, 650)

# Header
header = tk.Frame(root, bg=BG)
header.pack(fill="x", padx=30, pady=20)

tk.Label(header, text="V I C T O R",
         font=("Segoe UI", 25, "bold"),
         fg=GREEN, bg=BG).pack(side="left")

tk.Label(header, text="PERSONAL AI  /  COMMAND CENTER",
         font=("Segoe UI", 10),
         fg=MUTED, bg=BG).pack(side="right", pady=12)

# Main layout
main = tk.Frame(root, bg=BG)
main.pack(fill="both", expand=True, padx=25, pady=10)

# Sidebar
side = tk.Frame(main, bg=PANEL, width=210)
side.pack(side="left", fill="y", padx=(0, 20))
side.pack_propagate(False)

tk.Label(side, text="NAVIGATION",
         fg=CYAN, bg=PANEL,
         font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=20, pady=25)

for name in ["OVERVIEW", "VOICE SYSTEM", "AI CHAT",
             "MEMORY BANK", "FILE CENTER", "SYSTEM MONITOR", "SETTINGS"]:
    tk.Label(side, text="  ◈   " + name,
             fg=WHITE, bg=PANEL,
             font=("Segoe UI", 10),
             anchor="w", pady=15).pack(fill="x", padx=10)

# Main content
content = tk.Frame(main, bg=BG)
content.pack(side="left", fill="both", expand=True)

tk.Label(content, text="SYSTEM OVERVIEW",
         font=("Segoe UI", 22, "bold"),
         fg=WHITE, bg=BG).pack(anchor="w")

tk.Label(content, text="Victor is standing by.",
         font=("Segoe UI", 10),
         fg=MUTED, bg=BG).pack(anchor="w", pady=5)

# Center AI core
core_panel = tk.Frame(content, bg=PANEL)
core_panel.pack(fill="both", expand=True, pady=20)

canvas = tk.Canvas(core_panel, bg=PANEL,
                   highlightthickness=0, height=340)
canvas.pack(fill="both", expand=True)

def animate():
    canvas.delete("all")

    w = canvas.winfo_width()
    h = canvas.winfo_height()
    cx, cy = w // 2, h // 2

    t = time.time()

    for radius, color, width in [
        (105, GREEN, 2),
        (85, CYAN, 1),
        (65, GREEN, 1)
    ]:
        canvas.create_oval(
            cx-radius, cy-radius,
            cx+radius, cy+radius,
            outline=color, width=width
        )

    for i in range(36):
        angle = math.radians(i * 10 + t * 25)
        x1 = cx + 110 * math.cos(angle)
        y1 = cy + 110 * math.sin(angle)
        x2 = cx + 120 * math.cos(angle)
        y2 = cy + 120 * math.sin(angle)

        canvas.create_line(x1, y1, x2, y2,
                           fill=CYAN if i % 3 == 0 else GREEN)

    canvas.create_text(cx, cy-8, text="V",
                       fill=GREEN,
                       font=("Segoe UI", 42, "bold"))

    canvas.create_text(cx, cy+45,
                       text="VICTOR AI CORE",
                       fill=WHITE,
                       font=("Segoe UI", 10, "bold"))

    canvas.create_text(cx, cy+150,
                       text="●  LOCAL SYSTEM ONLINE",
                       fill=GREEN,
                       font=("Segoe UI", 10))

    root.after(50, animate)

# Bottom status panels
status = tk.Frame(content, bg=BG)
status.pack(fill="x", pady=(0, 15))

for title, value in [
    ("AI ENGINE", "QWEN 3.5 : 9B"),
    ("SPEECH INPUT", "FASTER-WHISPER"),
    ("VOICE OUTPUT", "MICROSOFT DAVID"),
    ("MEMORY", "SQLITE DATABASE")
]:
    card = tk.Frame(status, bg=PANEL, padx=15, pady=18)
    card.pack(side="left", fill="both", expand=True, padx=5)

    tk.Label(card, text=title, fg=MUTED,
             bg=PANEL, font=("Segoe UI", 9, "bold")).pack(anchor="w")

    tk.Label(card, text=value, fg=CYAN,
             bg=PANEL, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=8)

tk.Label(root, text="V I C T O R     |     LOCAL INTELLIGENCE SYSTEM",
         fg=MUTED, bg=BG,
         font=("Segoe UI", 9)).pack(pady=12)

animate()
root.mainloop()