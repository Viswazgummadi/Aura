# File: src/bot/client.py

import discord
import asyncio
import os
from discord.ext import commands

# Import configuration and the agent's core for the @mention handler
from src.core import config
from src.agent import core as agent_core

# =================================================================================
# Core Bot Class and Execution
# =================================================================================

class AuraBot(commands.Bot):
    def __init__(self):
        # Define intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        # Initialize the bot
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        """
        This is called once the bot is ready. It's the best place to load cogs.
        """
        print("Loading cogs...")
        # This code automatically finds and loads any file in the 'cogs' directory
        # that ends with .py.
        for filename in os.listdir('./src/bot/cogs'):
            if filename.endswith('.py') and not filename.startswith('__'):
                try:
                    # The path format is 'src.bot.cogs.cog_name'
                    await self.load_extension(f'src.bot.cogs.{filename[:-3]}')
                    print(f'  - Successfully loaded {filename}')
                except Exception as e:
                    print(f'  - Failed to load {filename}: {e}')
        
        print("Cogs loaded successfully.")

    async def on_ready(self):
        """Called when the bot is fully logged in and ready."""
        print('------')
        print(f'Logged on as {self.user} ({self.user.id})')
        print('Aura is online and ready.')
        print('------')

    async def on_message(self, message: discord.Message):
        """
        This event is triggered for every message the bot can see.
        """
        # Ignore messages sent by the bot itself
        if message.author == self.user:
            return

        # Handle @mentions for the AI agent
        if self.user.mentioned_in(message) and not message.mention_everyone:
            async with message.channel.typing():
                # Extract the prompt text from the message
                prompt = message.content.replace(f'<@!{self.user.id}>', '').replace(f'<@{self.user.id}>', '').strip()
                
                # Call the synchronous Gemini function in a separate thread
                # We will refactor this in a later phase to call the agent invoker
                response = await asyncio.get_running_loop().run_in_executor(
                    None, agent_core.get_gemini_response, prompt
                )
                await message.reply(response)
            return  # Stop further processing to avoid treating it as a command

        # Process regular commands (e.g., !ping, !events)
        await self.process_commands(message)

def run_bot():
    """The main entry point to start the bot."""
    bot = AuraBot()
    
    if config.DISCORD_BOT_TOKEN:
        bot.run(config.DISCORD_BOT_TOKEN)
    else:
        print("CRITICAL ERROR: DISCORD_BOT_TOKEN not found in .env file.")