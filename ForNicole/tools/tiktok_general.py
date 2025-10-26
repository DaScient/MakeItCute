import os
import random
import asyncio
from datetime import datetime
from collections import Counter, defaultdict

import pandas as pd

# ---------- CONFIGURATION ----------
API_KEYS = [
    "YTk2OGUxZjdiOTlmZWUxZDNlMzcwM2VlYzQ1NGVhM2YyNmM3MWVlMzQ1ODk2OTBkM2NiYmYx",
    "YzMxYWYxNjM0N2NmYTU3MzRiOTc0YWMzYTAyZWJmNTI2NGM3ODc5YzRhYWVkMDI4ZjIwZjhl",
    "OWYxMjhhYTEzYWU2MjdiNmIyMTVjNGFjNDQ5YTI1Zjg1MzM5YjIzYzNiNjdkZWFiZTQ0MjQ3"
]
selected_key = random.choice(API_KEYS)
os.environ["EULERSTREAM_API_KEY"] = selected_key

UNIQUE_ID = "aznboi_"    # Change to desired username
SAVE_TO_CSV = True       # Set to True to export logs
CSV_FILE = "tiktok_live_events.csv"

# ---------- INITIALIZATION ----------
from TikTokLive import TikTokLiveClient
from TikTokLive.events import (
    CommentEvent, GiftEvent, LikeEvent, ShareEvent, FollowEvent, EnvelopeEvent
)

# --- For text analytics & simple predictions ---
import re

class LiveAnalytics:
    def __init__(self):
        self.chat_counter = 0
        self.event_log = []
        self.user_counts = Counter()
        self.word_counts = Counter()
        self.engagement = defaultdict(lambda: {"comments": 0, "gifts": 0, "likes": 0, "shares": 0})
        self.last_minute_comments = []

    def log_event(self, event_type, user, message):
        now = datetime.utcnow().isoformat()
        self.event_log.append({"time": now, "event": event_type, "user": user, "message": message})
        if SAVE_TO_CSV:
            pd.DataFrame([self.event_log[-1]]).to_csv(CSV_FILE, mode="a", header=not os.path.exists(CSV_FILE), index=False)

    def update_analytics(self, event_type, user, message=None):
        self.engagement[user][event_type] += 1
        self.user_counts[user] += 1
        if event_type == "comments" and message:
            words = re.findall(r"\w+", message.lower())
            self.word_counts.update(words)
            self.last_minute_comments.append(datetime.utcnow())

    def trending_keywords(self, topn=5):
        return self.word_counts.most_common(topn)

    def most_active_users(self, topn=5):
        return self.user_counts.most_common(topn)

    def engagement_score(self, user):
        data = self.engagement[user]
        # Weighted engagement (customize as needed)
        return data["comments"] + 2 * data["gifts"] + 0.5 * data["likes"] + data["shares"]

    def recent_activity_spike(self):
        # Detect spikes in chat within last 60s
        now = datetime.utcnow()
        self.last_minute_comments = [t for t in self.last_minute_comments if (now - t).total_seconds() < 60]
        return len(self.last_minute_comments) > 25   # Threshold for "spike" (customize as needed)

analytics = LiveAnalytics()

# ---------- MAIN SCRIPT ----------
async def main():
    client = TikTokLiveClient(unique_id=UNIQUE_ID)
    print(f"Using API key: {selected_key[:8]}... Monitoring: @{UNIQUE_ID}")

    # --- Comment Listener ---
    @client.on(CommentEvent)
    async def on_comment(event: CommentEvent):
        analytics.log_event("comment", event.user.unique_id, event.comment)
        analytics.update_analytics("comments", event.user.unique_id, event.comment)
        print(f"[COMMENT] {event.user.nickname}: {event.comment}")

        # Respond to !command
        if event.comment.startswith("!"):
            # Here you can integrate GPT/LLM or custom responses
            print(f">>> Command received: {event.comment}")
            # await client.send_message("Your reply here") # Uncomment if you want to auto-respond

        # Notify on viral spike
        if analytics.recent_activity_spike():
            print("[ALERT] 🔥 Viral chat spike detected! Analyze or respond accordingly.")

    # --- Gift Listener ---
    @client.on(GiftEvent)
    async def on_gift(event: GiftEvent):
        analytics.log_event("gift", event.user.unique_id, event.gift.describe())
        analytics.update_analytics("gifts", event.user.unique_id)
        print(f"[GIFT] {event.user.nickname} sent a gift: {event.gift.describe()}")

    # --- Like Listener ---
    @client.on(LikeEvent)
    async def on_like(event: LikeEvent):
        analytics.log_event("like", event.user.unique_id, None)
        analytics.update_analytics("likes", event.user.unique_id)
        print(f"[LIKE] {event.user.nickname} liked the stream.")

    # --- Share Listener ---
    @client.on(ShareEvent)
    async def on_share(event: ShareEvent):
        analytics.log_event("share", event.user.unique_id, None)
        analytics.update_analytics("shares", event.user.unique_id)
        print(f"[SHARE] {event.user.nickname} shared the stream.")

    # --- Follow Listener ---
    @client.on(FollowEvent)
    async def on_follow(event: FollowEvent):
        analytics.log_event("follow", event.user.unique_id, None)
        print(f"[FOLLOW] {event.user.nickname} followed the streamer.")

    # --- Envelope/Other Events (advanced) ---
    @client.on(EnvelopeEvent)
    async def on_envelope(event: EnvelopeEvent):
        analytics.log_event("envelope", event.user.unique_id, "Red envelope event")
        print(f"[ENVELOPE] {event.user.nickname} triggered a red envelope event.")

    # --- (Optional) Add more event handlers as needed ---

    # --- Main run loop ---
    try:
        await client.start()
    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        # On shutdown, show summary analytics
        print("\n--- TikTokLive Analytics Summary ---")
        print(f"Top Users: {analytics.most_active_users()}")
        print(f"Trending Keywords: {analytics.trending_keywords()}")
        print("Engagement Scores:")
        for user, _ in analytics.most_active_users():
            print(f"  {user}: {analytics.engagement_score(user)}")
        print("Goodbye.")

# ---------- RUN ----------
if __name__ == "__main__":
    asyncio.run(main())
