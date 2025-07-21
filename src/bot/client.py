# In src/bot/client.py
import discord
import asyncio
import datetime
from discord.ext import commands
from src.core import config
from src.agent import core as agent_core
from src.gcp import calendar as google_calendar
from src.gcp import gmail as google_gmail

# =================================================================================
# UI Component: Calendar Event Edit Form (Modal)
# =================================================================================
class EventEditModal(discord.ui.Modal):
    def __init__(self, event: dict):
        super().__init__(title="Edit Calendar Event")
        self.event = event

        # Pre-fill form with existing event data
        summary = event.get('summary', '')
        description = event.get('description', '')
        location = event.get('location', '')
        start_str, end_str = "", ""
        
        # Format datetimes for easy editing
        if 'dateTime' in event['start']:
            start_dt = datetime.datetime.fromisoformat(event['start']['dateTime'])
            start_str = start_dt.strftime('%Y-%m-%d %H:%M')
            end_dt = datetime.datetime.fromisoformat(event['end']['dateTime'])
            end_str = end_dt.strftime('%Y-%m-%d %H:%M')
            
        self.summary_input = discord.ui.TextInput(label="Event Title", default=summary)
        self.start_input = discord.ui.TextInput(label="Start (YYYY-MM-DD HH:MM)", default=start_str)
        self.end_input = discord.ui.TextInput(label="End (YYYY-MM-DD HH:MM)", default=end_str)
        self.location_input = discord.ui.TextInput(label="Location", default=location, required=False)
        self.description_input = discord.ui.TextInput(label="Description", default=description, style=discord.TextStyle.paragraph, required=False)

        for item in [self.summary_input, self.start_input, self.end_input, self.location_input, self.description_input]:
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            # Convert user's simple time string back to timezone-aware ISO format
            start_dt = datetime.datetime.strptime(self.start_input.value, '%Y-%m-%d %H:%M').astimezone()
            end_dt = datetime.datetime.strptime(self.end_input.value, '%Y-%m-%d %H:%M').astimezone()
            start_iso, end_iso = start_dt.isoformat(), end_dt.isoformat()

            loop = asyncio.get_running_loop()
            updated_event = await loop.run_in_executor(
                None, google_calendar.update_event, self.event['id'], self.summary_input.value,
                start_iso, end_iso, self.description_input.value, self.location_input.value
            )
            
            if updated_event:
                await interaction.followup.send("✅ Event updated successfully!", ephemeral=True)
            else:
                await interaction.followup.send("❌ Failed to update the event. Check the bot's console.", ephemeral=True)
        except ValueError:
            await interaction.followup.send("❌ Invalid date/time format. Please use `YYYY-MM-DD HH:MM`.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"An unexpected error occurred: {e}", ephemeral=True)

# =================================================================================
# UI Component: Clickable Event "Card" Button
# =================================================================================
class EventView(discord.ui.View):
    def __init__(self, event: dict):
        super().__init__(timeout=None) # Buttons will not time out
        self.event = event
        
        summary = event.get('summary', 'No Title')
        time_str = "All-Day"
        if 'dateTime' in event['start']:
            start_dt = datetime.datetime.fromisoformat(event['start']['dateTime'])
            end_dt = datetime.datetime.fromisoformat(event['end']['dateTime'])
            time_str = f"{start_dt.strftime('%-I:%M %p')} - {end_dt.strftime('%-I:%M %p')}"
            
        button_label = f"{summary}  |  {time_str}"
        button_label = (button_label[:77] + '...') if len(button_label) > 80 else button_label

        self.edit_button = discord.ui.Button(label=button_label, style=discord.ButtonStyle.secondary, custom_id=f"edit_{event['id']}")
        self.edit_button.callback = self.button_callback
        self.add_item(self.edit_button)

    async def button_callback(self, interaction: discord.Interaction):
        modal = EventEditModal(self.event)
        await interaction.response.send_modal(modal)

# =================================================================================
# UI Component: Read-Only Mail "Card" Button
# =================================================================================
class MailDisplayView(discord.ui.View):
    def __init__(self, email_subject: str, email_sender: str):
        super().__init__(timeout=None)
        
        sender_name = email_sender.split('<')[0].strip().title().replace('"', '')
        button_label = f"{sender_name}: {email_subject}"
        button_label = (button_label[:77] + '...') if len(button_label) > 80 else button_label

        # This button is disabled, making it purely for display.
        self.add_item(discord.ui.Button(label=button_label, style=discord.ButtonStyle.secondary, disabled=True))

# =================================================================================
# Main Functionality Cog (Houses all commands)
# =================================================================================
class BotFunctionality(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='ping', help='Checks the bot\'s responsiveness.')
    async def ping(self, ctx: commands.Context):
        await ctx.send(f'Pong! 🏓 Latency: {round(self.bot.latency * 1000)}ms')

    @commands.command(name='events', help='Lists upcoming events as editable cards.')
    async def events(self, ctx: commands.Context):
        thinking_message = await ctx.send("📅 Fetching your calendar events...")
        loop = asyncio.get_running_loop()
        upcoming_events = await loop.run_in_executor(None, google_calendar.fetch_upcoming_events, 5)

        if not upcoming_events:
            return await thinking_message.edit(content="No upcoming events found.")
        
        await thinking_message.delete()
        for event in upcoming_events:
            await ctx.send(view=EventView(event))

    @commands.command(name='mail', help='Shows your latest unread emails.')
    async def mail(self, ctx: commands.Context):
        thinking_message = await ctx.send("📧 Fetching unread mail...")
        loop = asyncio.get_running_loop()
        try:
            unread_emails = await loop.run_in_executor(None, google_gmail.fetch_unread_emails, 5)
            if not unread_emails:
                return await thinking_message.edit(content="No unread emails found. You're all caught up!")
            
            await thinking_message.edit(content="**Here are your latest unread emails:**")
            for email in unread_emails:
                await ctx.send(view=MailDisplayView(email['subject'], email['sender']))
        except Exception as e:
            await thinking_message.edit(content=f"An error occurred: {e}")

# =================================================================================
# Core Bot Class and Execution
# =================================================================================
class AuraBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content, intents.members = True, True
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        await self.add_cog(BotFunctionality(self))
        print("Successfully loaded the BotFunctionality cog.")

    async def on_ready(self):
        print(f'Logged on as {self.user} ({self.user.id})')
        print('Aura is online and ready.')
        print('------')

    async def on_message(self, message: discord.Message):
        if message.author == self.user: return
        if self.user.mentioned_in(message) and not message.mention_everyone:
            async with message.channel.typing():
                prompt = message.content.replace(f'<@!{self.user.id}>', '').replace(f'<@{self.user.id}>', '').strip()
                response = await asyncio.get_running_loop().run_in_executor(None, agent_core.get_gemini_response, prompt)
                await message.reply(response)
            return
        await self.process_commands(message)

def run_bot():
    bot = AuraBot()
    if config.DISCORD_BOT_TOKEN:
        bot.run(config.DISCORD_BOT_TOKEN)
    else:
        print("CRITICAL ERROR: DISCORD_BOT_TOKEN not found.")