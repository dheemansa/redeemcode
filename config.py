import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram API Credentials
# Get these from https://my.telegram.org/apps
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")

# Session Name (This will create a session file to save your login)
SESSION_NAME = "session1"

# Optional: Restrict to specific chats?
# Set to None to listen to ALL chats you are in.
# Set to a list of usernames/IDs to filter (e.g., [-100123456789, 'my_channel'])
TARGET_CHATS = []

