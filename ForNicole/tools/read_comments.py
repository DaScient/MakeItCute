import os
import random
import asyncio

API_KEYS = [
    "YTk2OGUxZjdiOTlmZWUxZDNlMzcwM2VlYzQ1NGVhM2YyNmM3MWVlMzQ1ODk2OTBkM2NiYmYx",
    "YzMxYWYxNjM0N2NmYTU3MzRiOTc0YWMzYTAyZWJmNTI2NGM3ODc5YzRhYWVkMDI4ZjIwZjhl",
    "OWYxMjhhYTEzYWU2MjdiNmIyMTVjNGFjNDQ5YTI1Zjg1MzM5YjIzYzNiNjdkZWFiZTQ0MjQ3"
]

selected_key = random.choice(API_KEYS)
os.environ["EULERSTREAM_API_KEY"] = selected_key
print(f"Using API Key: {selected_key[:8]}...")

from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent

async def main():
    client = TikTokLiveClient(unique_id="aznboi_")
    
    @client.on(CommentEvent)
    async def on_comment(event: CommentEvent):
        print(f"{event.user.nickname}: {event.comment}")

    await client.start()

if __name__ == "__main__":
    asyncio.run(main())
