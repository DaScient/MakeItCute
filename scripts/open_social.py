#!/usr/bin/env python3
import webbrowser, json, sys
DEFAULTS = {
    "Discord": "https://discord.gg/your_invite",
    "TikTok": "https://www.tiktok.com/@your_handle",
    "Instagram": "https://www.instagram.com/your_handle",
    "X/Twitter": "https://twitter.com/your_handle",
    "YouTube": "https://youtube.com/@your_handle",
}
cfg_path = "social.json"
try:
    with open(cfg_path) as f:
        links = json.load(f)
except Exception:
    links = DEFAULTS
for _, url in links.items():
    webbrowser.open(url)
print("Opened social links. Edit social.json to customize.")
