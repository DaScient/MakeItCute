#!/usr/bin/env python3
# Neon ASCII Dashboard: hot pink on black; adorable and helpful.

import os, sys, time, webbrowser, subprocess, platform
from pathlib import Path

# ANSI helpers
RESET = "\033[0m"
PINK = "\033[38;5;205m"
BLACK_BG = "\033[48;5;232m"
BOLD = "\033[1m"
DIM = "\033[2m"

ASCII_LOGO = r"""
\033[38;5;219m
        ╭──────────────────────────────────────────────╮
        │                                              │
        │   \033[38;5;213m╭──╮   \033[38;5;219m╭──╮   \033[38;5;117m╭──╮   \033[38;5;213m╭──╮   \033[38;5;219m╭──╮   \033[38;5;117m╭──╮   │
        │   \033[38;5;213m│ P│\033[38;5;219mr│\033[38;5;117mi│\033[38;5;213mn│\033[38;5;219mc│\033[38;5;117me│\033[38;5;213ms│\033[38;5;219s│ \033[38;5;117mT│\033[38;5;213me│\033[38;5;219mr│\033[38;5;117mm│\033[38;5;213mi│\033[38;5;219mn│\033[38;5;117ma│\033[38;5;213ml│ │
        │   \033[38;5;213m╰──╯   \033[38;5;219m╰──╯   \033[38;5;117m╰──╯   \033[38;5;213m╰──╯   \033[38;5;219m╰──╯   \033[38;5;117m╰──╯   │
        │                                              │
        │      \033[38;5;213m✨ \033[38;5;219mPrincess Terminal\033[38;5;117m ✨                     │
        │        \033[38;5;219mThe prettiest shell in the realm 🐚         │
        │                                              │
        │   (\_/)  stay curious                        │
        │  (=’.’=) stay soft, stay powerful            │
        │  (")_(") code kindly 💻                      │
        ╰──────────────────────────────────────────────╯
\033[0m
"""

MENU = [
    ("Create/activate venv", "create_venv"),
    ("Install requirements", "install_requirements"),
    ("Run a friendly REPL (rich)", "run_repl"),
    ("Open docs (OS setup)", "open_docs"),
    ("Open GitHub repo", "open_repo"),
    ("Social pointables", "social_links"),
    ("Tiny tutor: tips & tricks", "tiny_tips"),
    ("Quit", "quit"),
]

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
REPO_URL = "https://github.com/dascient/makeitcute"

SOCIAL = {
    "Discord": "https://discord.gg/your_invite",
    "TikTok": "https://www.tiktok.com/@your_handle",
    "Instagram": "https://www.instagram.com/your_handle",
    "X/Twitter": "https://twitter.com/your_handle",
    "YouTube": "https://youtube.com/@your_handle",
}

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def print_header():
    print(f"{BLACK_BG}{PINK}{BOLD}{ASCII_LOGO}{RESET}")
    print(f"{PINK}{DIM}Hot pink. Pure black. Egregiously charming.{RESET}\n")

def prompt(menu):
    for idx, (label, _) in enumerate(menu, 1):
        print(f"{PINK}{idx:>2}. {label}{RESET}")
    print()
    val = input(f"{BOLD}{PINK}Choose an option: {RESET}")
    return int(val) if val.isdigit() and 1 <= int(val) <= len(menu) else 0

def open_file(path: Path):
    if os.name == "nt":
        os.startfile(str(path))
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)])
    else:
        subprocess.run(["xdg-open", str(path)])

def create_venv():
    venv = ROOT / ".venv"
    if not venv.exists():
        subprocess.check_call([sys.executable, "-m", "venv", str(venv)])
        print(f"{PINK}✨ Created .venv{RESET}")
    else:
        print(f"{PINK}✔ .venv already exists{RESET}")
    activate_msg = ".venv\\Scripts\\Activate.ps1" if os.name == "nt" else "source .venv/bin/activate"
    print(f"{DIM}Activate with: {activate_msg}{RESET}")
    input(f"{PINK}Press Enter to continue…{RESET}")

def install_requirements():
    req = ROOT / "requirements.txt"
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(req)])
    print(f"{PINK}🧁 Requirements installed!{RESET}")
    input(f"{PINK}Press Enter to continue…{RESET}")

def run_repl():
    banner = f"{PINK}Welcome to the Friendly REPL. Try: print('hiya 💖') {RESET}"
    try:
        import code
        code.interact(banner=banner, local={})
    except Exception as e:
        print(f"{PINK}REPL failed: {e}{RESET}")
    input(f"{PINK}Press Enter to continue…{RESET}")

def open_docs():
    plat = platform.system().lower()
    target = {
        "darwin": DOCS / "INSTALL-macOS.md",
        "windows": DOCS / "INSTALL-windows.md",
        "linux": DOCS / "INSTALL-linux.md",
    }.get(plat, DOCS)
    try:
        open_file(target)
    except Exception:
        webbrowser.open(REPO_URL + "/tree/main/docs")

def open_repo():
    webbrowser.open(REPO_URL)

def social_links():
    print(f"{PINK}{BOLD}Social pointables:{RESET}")
    for name, url in SOCIAL.items():
        print(f" - {name}: {url}")
    print("\nTip: replace the placeholders in neon_dash.py → SOCIAL dict.")
    input(f"{PINK}Press Enter to continue…{RESET}")

def tiny_tips():
    tips = [
        "Use `python -m pip` to avoid version confusion.",
        "Name venv `.venv` so editors auto-detect it.",
        "Run `python -m http.server` to share a folder locally.",
        "Use f-strings for readable formatting: f'{2+2=}' → 2+2=4",
        "pip freeze > requirements.txt to capture deps.",
    ]
    for t in tips:
        print(f"{PINK}• {t}{RESET}")
    input(f"{PINK}Press Enter to continue…{RESET}")

def quit():
    print(f"{PINK}Stay cute, stay curious. Bye!{RESET}")
    sys.exit(0)

def main():
    while True:
        clear()
        print_header()
        choice = prompt(MENU)
        if choice == 0:
            continue
        _, fn = MENU[choice-1]
        globals()[fn]()

if __name__ == "__main__":
    main()
