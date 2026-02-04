import asyncio
import sys
import time
import os
import config
from concurrent.futures import ThreadPoolExecutor
from app.ocr import extract_redeem_code
from app.telegram import TelegramListener
from autoredeem.autoredeem import AutoRedeemer

# Configuration for Parallelism
NUM_BOTS = 3  # Number of parallel Chrome instances


class RedemptionPool:
    """
    Manages a pool of AutoRedeemer bots to handle multiple codes simultaneously.
    """

    def __init__(self, size=3):
        self.size = size
        self.pool = asyncio.Queue()  # Stores available bot instances
        self.executor = ThreadPoolExecutor(
            max_workers=size
        )  # For running blocking Selenium calls

    def initialize_bots(self):
        """
        Creates the bot instances, each with a unique profile path.
        """
        print(f"[POOL] Initializing {self.size} AutoRedeemer bots...")

        # Ensure base profile directory exists
        base_profile_dir = "chrome_profiles"
        os.makedirs(base_profile_dir, exist_ok=True)

        for i in range(self.size):
            profile_path = os.path.join(base_profile_dir, f"bot_{i + 1}")
            # Initialize bot (headless=False for debugging, ideally True for prod)
            bot = AutoRedeemer(
                dry_run=False, headless=True, timeout=20, profile_path=profile_path
            )
            # Tag the bot with an ID
            bot.worker_id = i + 1
            self.pool.put_nowait(bot)
            print(f"[POOL] Bot #{i + 1} Ready (Profile: {profile_path})")

    async def redeem_async(self, code):
        """
        Acquires a bot from the pool, runs redemption in a thread, and returns the bot to the pool.
        """
        # Wait for an available bot
        bot = await self.pool.get()

        try:
            # Run the blocking Selenium code in a separate thread
            # This prevents freezing the main asyncio loop
            loop = asyncio.get_running_loop()
            status = await loop.run_in_executor(self.executor, bot.redeem_code, code)

            return status, bot.worker_id
        finally:
            # Always return the bot to the pool, even if it crashed
            self.pool.put_nowait(bot)


async def ocr_worker(image_queue, code_queue):
    """
    Consumer 1: Pulls images, runs OCR (fast), pushes codes to code_queue.
    """
    print("[OCR WORKER] Ready to process images.")

    while True:
        item = await image_queue.get()
        image_bytes = item["image"]
        chat_title = item.get("chat_title", "Unknown")
        arrival_time = item["timestamp"]

        lag = time.time() - arrival_time
        print(f"\n>>> [OCR] Scanning image from '{chat_title}' (Lag: {lag:.3f}s)")

        # OCR Extraction
        ocr_start = time.time()
        code = extract_redeem_code(image_bytes, debug=True)
        ocr_duration = time.time() - ocr_start

        if code:
            print(f"✅ [OCR] FOUND CODE: {code} ({ocr_duration:.3f}s)")
            # Push to the redemption queue
            await code_queue.put(code)
        else:
            print(f"❌ [OCR] No code found ({ocr_duration:.3f}s)")

        image_queue.task_done()


async def redemption_manager(code_queue, bot_pool):
    """
    Consumer 2: Pulls codes and schedules them on the bot pool.
    """
    print("[REDEEM MANAGER] Waiting for codes...")

    while True:
        code = await code_queue.get()

        # Fire and forget (or rather, fire and await result asynchronously)
        # We wrap it in a task so we don't block waiting for this specific redemption
        asyncio.create_task(handle_redemption(bot_pool, code))

        code_queue.task_done()


async def handle_redemption(bot_pool, code):
    """
    Helper to run redemption and log the result.
    """
    start_time = time.time()

    status, worker_id = await bot_pool.redeem_async(code)
    duration = time.time() - start_time

    print(
        f"🚀 [REDEEM FINISHED] Code: {code} | Status: {status} | Bot #{worker_id} | Time: {duration:.3f}s"
    )

    # Log to file
    with open("data/codes.txt", "a") as f:
        f.write(f"{code} | {status} | {time.ctime()} | Bot #{worker_id}\n")


async def main():
    # 1. Validation
    if config.API_ID == 12345678:
        print("CRITICAL: Please configure 'config.py' with your API credentials.")
        sys.exit(1)

    # 2. Setup Queues
    image_queue = asyncio.Queue()  # Telegram -> OCR
    code_queue = asyncio.Queue()  # OCR -> Redeemer

    # 3. Initialize Bot Pool
    bot_pool = RedemptionPool(size=NUM_BOTS)
    bot_pool.initialize_bots()

    # 4. Initialize Telegram Listener
    listener = TelegramListener(
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        session_name=f"data/{config.SESSION_NAME}",
        image_queue=image_queue,
        target_chats=config.TARGET_CHATS,
    )

    # 5. Launch Tasks
    tasks = [
        asyncio.create_task(listener.start()),
        asyncio.create_task(ocr_worker(image_queue, code_queue)),
        asyncio.create_task(redemption_manager(code_queue, bot_pool)),
    ]

    print(f"=== Contest Bot Online (Parallel Mode: {NUM_BOTS} Bots) ===")
    print(f"Target Chats: {config.TARGET_CHATS if config.TARGET_CHATS else 'ALL'}")
    print("Press Ctrl+C to stop.")

    # Keep running
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\n[SYSTEM] Shutting down...")

