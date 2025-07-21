# In src/bot/client.py
import discord
import asyncio
from discord.ext import commands
from src.core import config
from src.agent import core as agent_core
from src.gcp import calendar as google_calendar

# --- The Commands Cog ---
class BotFunctionality(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='ping', help='Responds with pong and the bot\'s latency.')
    async def ping(self, ctx: commands.Context):
        """Simple command to check bot responsiveness and API latency."""
        latency = round(self.bot.latency * 1000)
        await ctx.send(f'Pong! 🏓 Latency: {latency}ms')

    @commands.command(name='events', help='Fetches the next 5 events from your Google Calendar.')
    async def events(self, ctx: commands.Context):
        """
        Fetches and displays upcoming Google Calendar events in a rich embed.
        """
        await ctx.send("📅 Checking your calendar, one moment...")
        
        loop = asyncio.get_running_loop()
        try:
            # The calendar function now returns a fully formed embed
            event_embed = await loop.run_in_executor(
                None, google_calendar.list_upcoming_events
            )
            # Send the embed object
            await ctx.send(embed=event_embed)
        except Exception as e:
            await ctx.send("A critical error occurred. I couldn't process the calendar request.")
            print(f"Error in !events command: {e}")

# --- The Main Bot Class ---
class AuraBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        """This is called automatically before the bot logs in."""
        await self.add_cog(BotFunctionality(self))
        print("Successfully loaded the BotFunctionality cog.")

    async def on_ready(self):
        """Called when the bot is successfully connected and ready."""
        print(f'Logged on as {self.user} ({self.user.id})')
        print('Aura is online and ready.')
        print('------')

    async def on_message(self, message: discord.Message):
        """Called for every message. Handles AI mentions and processes commands."""
        if message.author == self.user:
            return

        if self.user.mentioned_in(message) and not message.mention_everyone:
            async with message.channel.typing():
                prompt = message.content.replace(f'<@!{self.user.id}>', '').replace(f'<@{self.user.id}>', '').strip()
                print(f'Received prompt from {message.author}: "{prompt}"')
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(
                    None, agent_core.get_gemini_response, prompt
                )
                await message.reply(response)
            return

        await self.process_commands(message)

# --- The Entry Point ---
def run_bot():
    """Initializes and runs the AuraBot."""
    bot = AuraBot()
    if config.DISCORD_BOT_TOKEN:
        bot.run(config.DISCORD_BOT_TOKEN)
    else:
        print("CRITICAL ERROR: DISCORD_BOT_TOKEN not found.")