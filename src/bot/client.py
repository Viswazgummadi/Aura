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
                    print(f'  - Successfully loaded {filename}')
                except Exception as e:
                    print(f'  - Failed to load {filename}: {e}')
        
        print("Cogs loaded successfully.")

        webserver.run_webserver(self) 
        print(f"Flask web server setup complete.")

    async def on_ready(self):
        print('------')
        print(f'Logged on as {self.user} ({self.user.id})')
        print('Aura is online and ready.')
        print('------')

        self.loop.create_task(self.run_initial_gmail_sync())

    async def run_initial_gmail_sync(self):
        print("--- Initiating initial Gmail history sync as background task ---")
        try:
            # --- MODIFIED "FRESH START" LOGIC ---
            last_tracker_history_id = gmail_history_tracker.get_last_history_id()

            # THIS IS THE CORE OF THE NEW "FRESH START" BEHAVIOR
            if last_tracker_history_id is None:
                print(">>> First-time setup detected. Performing a 'Fresh Start'.")
                print(">>> All existing emails will be ignored. Notifications will begin for new emails from this point forward.")
                
                # 1. Get the current state of the mailbox without fetching any emails.
                current_api_history_id = await self.loop.run_in_executor(None, gmail_tool.get_latest_history_id_from_gmail_api)
                
                # 2. Save this as our baseline.
                gmail_history_tracker.set_last_history_id(current_api_history_id)
                
                # 3. Also grab the email address for future checks.
                try:
                    service = await self.loop.run_in_executor(None, gmail_tool.build_google_service, 'gmail', 'v1')
                    profile = await self.loop.run_in_executor(None, service.users().getProfile(userId='me').execute)
                    tracker_email_address = profile.get('emailAddress')
                    gmail_history_tracker.set_current_email_address(tracker_email_address)
                    print(f">>> Baseline established. Tracker's historyId is set to {current_api_history_id} for {tracker_email_address}.")
                except Exception as e:
                    print(f"WARNING: Could not get email address for tracker during fresh start: {e}.")

                print("--- Initial Gmail 'Fresh Start' sync complete ---")
                return # We are done, exit the function.

            # --- END MODIFIED LOGIC ---

            # This code below will now only run on subsequent restarts, not the very first one.
            print(">>> Existing history ID found. Syncing any messages received since last run...")
            messages_to_process, new_history_id_to_save = await self.loop.run_in_executor(
                None, gmail_tool.fetch_new_messages_for_processing_from_api, last_tracker_history_id
            )

            if messages_to_process:
                print(f"DISCORD_BOT: Found {len(messages_to_process)} catch-up messages during startup sync. Notifying owner.")
                owner = self.get_user(config.DISCORD_OWNER_ID)
                if owner:
                    for msg in messages_to_process:
                        await owner.send(
                            f"📧 Catch-up Mail: **{msg['subject']}** from **{msg['sender'].split('<')[0].strip()}**"
                            f" (ID: `{msg['id']}`)"
                        )
                        await self.loop.run_in_executor(None, gmail_tool.mark_message_as_read, msg['id'])
                        gmail_history_tracker.add_processed_message_id(msg['id'])
                    
                    gmail_history_tracker.set_last_history_id(new_history_id_to_save)
                    print(f"DISCORD_BOT: Initial sync history tracker updated to {new_history_id_to_save}")
                else:
                    print("DISCORD_BOT WARNING: Owner user object not found, cannot send DMs for catch-up sync.")
            else:
                print("DISCORD_BOT: No new messages found during catch-up sync. Tracker is up to date.")
                # We can still advance the history ID to the absolute latest, just in case.
                current_api_history = gmail_tool.get_latest_history_id_from_gmail_api()
                if current_api_history > (last_tracker_history_id or 0):
                    gmail_history_tracker.set_last_history_id(current_api_history)
                    print(f"DISCORD_BOT: History tracker advanced to current Gmail API history: {current_api_history}.")

        except Exception as e:
            print(f"DISCORD_BOT ERROR during initial Gmail sync: {e}")
            owner = self.get_user(config.DISCORD_OWNER_ID)
            if owner:
                await owner.send(f"❌ Error during initial Gmail sync: `{e}`. Subsequent mail notifications may be affected.")
        print("--- Initial Gmail history sync complete ---")

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