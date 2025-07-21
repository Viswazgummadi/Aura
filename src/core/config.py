# In src/core/config.py
import os
from dotenv import load_dotenv

# This line finds the .env file in your project folder and loads its contents
load_dotenv()

# This line retrieves the specific token value
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")