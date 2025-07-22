# File: src/bot/cogs/tools_cog.py

import discord
import asyncio
from discord.ext import commands

# Import the functions from our refactored gcp modules
from src.agent.tools import calendar as google_calendar
from src.agent.tools import gmail as google_gmail

# Import the UI components from their new, dedicated files
from src.bot.ui.event_ui import EventView
from src.bot.ui.mail_ui import MailDisplayView


class ToolsCog(commands.Cog):
    """
    A cog for general purpose tools like ping, calendar, and mail.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='ping', help='Checks the bot\'s responsiveness.')
    async def ping(self, ctx: commands.Context):
        await ctx.send(f'Pong! 🏓 Latency: {round(self.bot.latency * 1000)}ms')

    @commands.command(name='events', help='Lists upcoming events as editable cards.')
    async def events(self, ctx: commands.Context):
        thinking_message = await ctx.send("📅 Fetching your calendar events...")
        loop = asyncio.get_running_loop()
        try:
            # Note: We are importing from a path that doesn't exist yet (agent/tools).
            # This is part of the plan. We will create these files next.
            upcoming_events = await loop.run_in_executor(None, google_calendar.fetch_upcoming_events, 5)
            if not upcoming_events:
                return await thinking_message.edit(content="No upcoming events found.")
            
            await thinking_message.delete()
            for event in upcoming_events:
                # Use the imported EventView
                await ctx.send(view=EventView(event))
        except Exception as e:
            await thinking_message.edit(content=f"An error occurred: `{e}`")

    @commands.command(name='mail', help='Shows your latest unread emails.')
    async def mail(self, ctx: commands.Context):
        thinking_message = await ctx.send("📧 Fetching unread mail...")
        loop = asyncio.get_running_loop()
        try:
            unread_emails = await loop.run_in_executor(None, google_gmail.fetch_unread_emails, 5)
            if not unread_emails:
                return await thinking_message.edit(content="No unread emails found!")
            
            await thinking_message.edit(content="**Here are your latest unread emails:**")
            for email in unread_emails:
                # Use the imported MailDisplayView
                await ctx.send(view=MailDisplayView(email['subject'], email['sender']))
        except Exception as e:
            await thinking_message.edit(content=f"An error occurred: `{e}`")


async def setup(bot: commands.Bot):
    """This special function is called by discord.py when loading a cog."""
    await bot.add_cog(ToolsCog(bot))