# File: src/bot/cogs/tools_cog.py

import discord
import asyncio
from discord.ext import commands
import datetime
# Import the functions from our refactored gcp modules
from src.agent.tools import calendar as google_calendar
from src.agent.tools import gmail as google_gmail
from src.agent.tools import gmail_watcher

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

    # In src/bot/cogs/tools_cog.py, replace the create_event command with this final version

    @commands.command(name='create_event', help='(TEST) Creates a new calendar event.')
    @commands.is_owner()
    async def create_event(self, ctx: commands.Context, summary: str, start_str: str, end_str: str):
        """
        A test command to create a calendar event with specific times.
        Responds with an interactive event view upon success.
        Usage: !create_event "Event Title" "YYYY-MM-DD HH:MM" "YYYY-MM-DD HH:MM"
        """
        thinking_message = await ctx.send(f"📅 Creating event '{summary}'...")
        try:
            # 1. Parse the string inputs into datetime objects
            start_dt = datetime.datetime.strptime(start_str, '%Y-%m-%d %H:%M').astimezone()
            end_dt = datetime.datetime.strptime(end_str, '%Y-%m-%d %H:%M').astimezone()
            
            # 2. Convert to ISO 8601 format
            start_iso = start_dt.isoformat()
            end_iso = end_dt.isoformat()

            # 3. Call the tool function in an executor.
            # We must pass arguments positionally, not by keyword.
            loop = asyncio.get_running_loop()
            new_event = await loop.run_in_executor(
                None, 
                google_calendar.create_new_event,
                summary,          # summary
                start_iso,        # start_time_iso
                end_iso,          # end_time_iso
                "Created by Aura Bot", # description (optional)
                "Virtual"         # location (optional)
            )

            # 4. Report success using the interactive EventView
            if new_event:
                await thinking_message.delete() # Clean up the "Creating..." message
                
                # Create a confirmation embed
                embed = discord.Embed(
                    title="✅ Event Created Successfully",
                    color=discord.Color.green()
                )
                # Send the embed AND the interactive view
                await ctx.send(embed=embed, view=EventView(new_event))
            else:
                await thinking_message.edit(content="❌ Failed to create the event for an unknown reason.")

        except ValueError:
            await thinking_message.edit(content="❌ **Invalid date format!** Please use `YYYY-MM-DD HH:MM` for start and end times.")
        except Exception as e:
            # We print the full error to the console for easier debugging
            print(f"Error in !create_event: {e}") 
            await thinking_message.edit(content=f"An unexpected error occurred. Please check the console.")
    @commands.command(name='watchmail', help='Starts real-time Gmail notifications.')
    @commands.is_owner()
    async def watch_mail(self, ctx: commands.Context):
        """Initiates real-time Gmail push notifications."""
        await ctx.send("📧 Attempting to start real-time Gmail notifications...")
        loop = asyncio.get_running_loop()
        try:
            response = await loop.run_in_executor(None, gmail_watcher.watch_gmail_inbox)
            if response:
                embed = discord.Embed(
                    title="✅ Gmail Watch Started",
                    description=f"You will now receive notifications for new emails. Expires: {response.get('expirationHistoryId')}",
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Failed to start Gmail watch for an unknown reason.")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: `{e}`. Ensure you have granted all necessary Gmail API permissions.")
            print(f"Error watching mail: {e}")

    @commands.command(name='unwatchmail', help='Stops real-time Gmail notifications.')
    @commands.is_owner()
    async def unwatch_mail(self, ctx: commands.Context):
        """Stops real-time Gmail push notifications."""
        await ctx.send("📧 Attempting to stop real-time Gmail notifications...")
        loop = asyncio.get_running_loop()
        try:
            if await loop.run_in_executor(None, gmail_watcher.stop_gmail_inbox_watch):
                await ctx.send("✅ Gmail watch stopped successfully.")
            else:
                await ctx.send("❌ Failed to stop Gmail watch.")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: `{e}`.")
            print(f"Error unwaching mail: {e}")
            
async def setup(bot: commands.Bot):
    """This special function is called by discord.py when loading a cog."""
    await bot.add_cog(ToolsCog(bot))