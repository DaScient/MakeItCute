import pytchat
import time
import logging

YOUTUBE_VIDEO_ID = "AJ53jNaA5Fo"

COMMAND_MAP = {
    "!up": "up",
    "!down": "down",
    "!left": "left",
    "!right": "right",
    "!a": "a",
    "!b": "b",
    "!start": "enter",
    "!select": "shift",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def handle_comment(author, message):
    msg_lower = message.lower()
    if msg_lower.startswith("!"):
        cmd = msg_lower.split()[0]
        if cmd in COMMAND_MAP:
            logging.info(f"{author} issued command: {cmd} -> {COMMAND_MAP[cmd]}")
            # Instead of keyboard.press, send command to your game logic here
        else:
            logging.info(f"{author} issued unrecognized command: {cmd}")

def youtube_comment_listener():
    chat = pytchat.create(video_id=YOUTUBE_VIDEO_ID)
    logging.info("Started YouTube live chat listener.")
    while chat.is_alive():
        for c in chat.get().sync_items():
            handle_comment(c.author.name, c.message)
        time.sleep(0.1)

if __name__ == "__main__":
    youtube_comment_listener()
