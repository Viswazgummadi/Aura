# File: src/bot/client.py

import discord
import asyncio
import os
from discord.ext import commands
from discord.ext.commands import Bot

from src.core import config
from src.agent import invoker
from src.bot import webserver
from src.agent.tools import gmail as gmail_tool
import gmail_history_tracker
from gmail_history_tracker import GMAIL_PROCESSING_LOCK # <-- IMPORT THE LOCK

class AuraBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix='!', intents=intents, owner_id=config.DISCORD_OWNER_ID)

    async def setup_hook(self):
        print("Loading cogs...")
        for filename in os.listdir('./src/bot/cogs'):
            if filename.endswith('.py') and not filename.startswith('__'):
                try:
                    await self.load_extension(f'src.bot.cogs.{filename[:-3]}')
                except Exception as e:
                    print(f'  - Failed to load {filename}: {e}')
        
        webserver.run_webserver(self) 

    async def on_ready(self):
        print('------')
        print(f'Logged on as {self.user} ({self.user.id})')
        print('Aura is online and ready.')
        print('------')

        self.loop.create_task(self.run_initial_gmail_sync())

    async def run_initial_gmail_sync(self):
        async with GMAIL_PROCESSING_LOCK: # <-- ACQUIRE THE LOCK
            print("\n--- [LOCKED] Initiating initial Gmail sync ---")
            try:
                last_tracker_history_id = gmail_history_tracker.get_last_history_id()

                if last_tracker_history_id is None:
                    print("SYNC: First-time setup. Performing a 'Fresh Start'.")
                    current_api_history_id = await self.loop.run_in_executor(None, gmail_tool.get_latest_history_id_from_gmail_api)
                    gmail_history_tracker.set_last_history_id(current_api_history_id)
                    
                    service = await self.loop.run_in_executor(None, gmail_tool.build_google_service, 'gmail', 'v1')
                    profile = await self.loop.run_in_executor(None, service.users().getProfile(userId='me').execute)
                    tracker_email_address = profile.get('emailAddress')
                    gmail_history_tracker.set_current_email_address(tracker_email_address)
                    print(f"SYNC: Baseline established for {tracker_email_address}.")
                    
                    print("--- [UNLOCKED] Initial 'Fresh Start' sync complete ---\n")
                    return

                print("SYNC: Existing history found. Syncing messages since last run...")
                messages_to_process, new_history_id_to_save = await self.loop.run_in_executor(
                    None, gmail_tool.fetch_new_messages_for_processing_from_api, last_tracker_history_id
                )

                if messages_to_process:
                    print(f"SYNC: Found {len(messages_to_process)} catch-up messages. Notifying owner.")
                    owner = self.get_user(config.DISCORD_OWNER_ID)
                    if owner:
                        for msg in messages_to_process:
                            await owner.send(
                                f"📧 Catch-up Mail: **{msg['subject']}** from **{msg['sender'].split('<')[0].strip()}**"
                            )
                            await self.loop.run_in_executor(None, gmail_tool.mark_message_as_read, msg['id'])
                            gmail_history_tracker.add_processed_message_id(msg['id'])
                        
                        gmail_history_tracker.set_last_history_id(new_history_id_to_save)
                    else:
                        print("SYNC WARNING: Owner not found, cannot send DMs.")
                else:
                    print("SYNC: No new messages found. Advancing history tracker.")
                    current_api_history = await self.loop.run_in_executor(None, gmail_tool.get_latest_history_id_from_gmail_api)
                    if current_api_history > (last_tracker_history_id or 0):
                        gmail_history_tracker.set_last_history_id(current_api_history)

            except Exception as e:
                print(f"SYNC ERROR: {e}")
            
            print("--- [UNLOCKED] Initial sync complete ---\n")
    
    # ... (rest of the file is the same)
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if message.content.startswith(self.command_prefix):
            await self.process_commands(message)
            return

        is_in_aura_channel = (config.AURA_CHANNEL_ID and message.channel.id == config.AURA_CHANNEL_ID)
        is_a_mention = self.user.mentioned_in(message)

        if is_in_aura_channel or is_a_mention:
            await invoker.handle_mention(message)
            return

def run_bot():
    bot = AuraBot()
    if config.DISCORD_BOT_TOKEN:
        bot.run(config.DISCORD_BOT_TOKEN)
    else:
        print("CRITICAL ERROR: DISCORD_BOT_TOKEN not found in .env file.")