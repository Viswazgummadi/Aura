# File: src/bot/ui/event_ui.py

import discord
import asyncio
import datetime

# Note: We need to do a "type-only" import for the tools to avoid circular dependencies.
# This is a common pattern in larger discord.py bots.
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.agent.tools import calendar as google_calendar

class EventEditModal(discord.ui.Modal):
    def __init__(self, event: dict):
        super().__init__(title="Edit Calendar Event")
        self.event = event
        
        summary = event.get('summary', '')
        description = event.get('description', '')
        location = event.get('location', '')
        start_str, end_str = "", ""

        if 'dateTime' in event['start']:
            start_dt = datetime.datetime.fromisoformat(event['start']['dateTime'])
            end_dt = datetime.datetime.fromisoformat(event['end']['dateTime'])
            start_str = start_dt.strftime('%Y-%m-%d %H:%M')
            end_str = end_dt.strftime('%Y-%m-%d %H:%M')
        
        self.summary_input = discord.ui.TextInput(label="Event Title", default=summary, style=discord.TextStyle.short, required=True)
        self.start_time_input = discord.ui.TextInput(label="Start (YYYY-MM-DD HH:MM)", default=start_str, style=discord.TextStyle.short, required=True)
        self.end_time_input = discord.ui.TextInput(label="End (YYYY-MM-DD HH:MM)", default=end_str, style=discord.TextStyle.short, required=True)
        self.location_input = discord.ui.TextInput(label="Location", default=location, style=discord.TextStyle.short, required=False)
        self.description_input = discord.ui.TextInput(label="Description", default=description, style=discord.TextStyle.paragraph, required=False)

        for item in [self.summary_input, self.start_time_input, self.end_time_input, self.location_input, self.description_input]:
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        # We need to import the calendar tools here, inside the function,
        # to make the type-only import work correctly.
        from src.agent.tools import calendar as google_calendar

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            start_dt = datetime.datetime.strptime(self.start_time_input.value, '%Y-%m-%d %H:%M').astimezone()
            end_dt = datetime.datetime.strptime(self.end_time_input.value, '%Y-%m-%d %H:%M').astimezone()
            start_iso = start_dt.isoformat()
            end_iso = end_dt.isoformat()

            updated_event = await asyncio.get_running_loop().run_in_executor(
                None, 
                google_calendar.update_event,
                self.event['id'], 
                self.summary_input.value, 
                start_iso, 
                end_iso, 
                self.description_input.value, 
                self.location_input.value
            )
            if updated_event:
                await interaction.followup.send("✅ Event updated!", ephemeral=True)
            else:
                await interaction.followup.send("❌ Update failed.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

class EventView(discord.ui.View):
    def __init__(self, event: dict):
        super().__init__(timeout=None)
        self.event = event
        
        summary = event.get('summary', 'No Title')
        time_str = "All-Day"
        if 'dateTime' in event['start']:
            start_dt = datetime.datetime.fromisoformat(event['start']['dateTime'])
            end_dt = datetime.datetime.fromisoformat(event['end']['dateTime'])
            time_str = f"{start_dt.strftime('%-I:%M %p')} - {end_dt.strftime('%-I:%M %p')}"
        
        button_label = f"{summary}  |  {time_str}"
        if len(button_label) > 80:
            button_label = button_label[:77] + '...'
            
        edit_button = discord.ui.Button(label=button_label, style=discord.ButtonStyle.secondary, custom_id=f"edit_{event['id']}")
        edit_button.callback = self.button_callback
        self.add_item(edit_button)

    async def button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(EventEditModal(self.event))