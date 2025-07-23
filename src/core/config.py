# File: src/core/config.py (Complete Final Version)

import os
from dotenv import load_dotenv

# This line finds the .env file in your project folder and loads its contents
load_dotenv()

# Load Discord Bot Token
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not DISCORD_BOT_TOKEN:
    print("CRITICAL WARNING: DISCORD_BOT_TOKEN not found in .env file.")

# Load Google API Key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("CRITICAL WARNING: GOOGLE_API_KEY not found in .env file.")

# Load Aura Channel ID
try:
    AURA_CHANNEL_ID = int(os.getenv("AURA_CHANNEL_ID"))
except (ValueError, TypeError):
    AURA_CHANNEL_ID = None
    print("WARNING: AURA_CHANNEL_ID not found or invalid in .env. Dedicated channel features may not work.")

# Load Discord Owner ID
try:
    DISCORD_OWNER_ID = int(os.getenv("DISCORD_OWNER_ID"))
except (ValueError, TypeError):
    DISCORD_OWNER_ID = None
    print("WARNING: DISCORD_OWNER_ID not found or invalid in .env. Bot owner commands may not work correctly, and DMs to owner may fail.")