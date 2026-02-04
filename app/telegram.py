from telethon import TelegramClient, events
import asyncio
import time

class TelegramListener:
    def __init__(self, api_id, api_hash, session_name, image_queue, target_chats=None):
        """
        :param image_queue: An asyncio.Queue to put images into.
        """
        self.client = TelegramClient(session_name, api_id, api_hash)
        self.queue = image_queue
        self.target_chats = target_chats

        # Register handler
        self.client.add_event_handler(self.handler, events.NewMessage)

    async def handler(self, event):
        if not event.photo:
            return

        # Caption Filter
        caption = event.text or ""
        if "surprise" not in caption.lower():
            return

        # Chat Filtering
        chat = await event.get_chat()
        chat_id = event.chat_id
        chat_username = chat.username if hasattr(chat, 'username') else None
        
        # Safe title extraction
        chat_title = getattr(chat, 'title', 'Private Chat')
        
        if self.target_chats:
            is_target = chat_id in self.target_chats
            if not is_target and chat_username:
                is_target = chat_username in self.target_chats
            
            if not is_target:
                return
            print(f"\n[+] QUEUED: Image from {chat_title}")
        else:
            print(f"\n[+] QUEUED: Image from {chat_title}")

        # Download to memory immediately
        try:
            start_time = time.time()
            image_bytes = await event.download_media(file=bytes)
            
            # Put data into the queue for main_worker.py to handle
            # We pass a dictionary so we can carry metadata if needed later
            await self.queue.put({
                'image': image_bytes,
                'timestamp': start_time,
                'chat_id': chat_id,
                'chat_title': chat_title
            })
            
        except Exception as e:
            print(f"Error queuing image: {e}")

    async def start(self):
        print("Connecting to Telegram...")
        await self.client.start()
        print("Listener started... Waiting for images.")
        await self.client.run_until_disconnected()
