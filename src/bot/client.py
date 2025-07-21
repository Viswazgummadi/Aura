# In src/bot/client.py
import discord
import asyncio
import datetime
import os
from discord.ext import commands
from src.core import config
from src.agent import core as agent_core
from src.gcp import calendar as google_calendar
from src.gcp import gmail as google_gmail

# =================================================================================
# Authentication Cog
# =================================================================================
class AuthCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='auth', help='Authenticate with your Google account.')
    @commands.is_owner()
    async def auth(self, ctx: commands.Context):
        """Starts the Google authentication process."""
        await ctx.author.send(
            "Starting Google authentication...\n"
            "The bot will now print a URL in its console. Please open that URL in your browser to continue."
        )
        await ctx.message.add_reaction('✅')

        loop = asyncio.get_running_loop()
        try:
            # This will now print the URL in the console and wait.
            await loop.run_in_executor(None, google_calendar.run_auth_flow)
            
            embed = discord.Embed(
                title="✅ Authentication Successful",
                description="I am now connected to your Google account. You can use the `!events` and `!mail` commands.",
                color=discord.Color.green()
            )
            await ctx.author.send(embed=embed)
        except Exception as e:
            await ctx.author.send(f"An error occurred during authentication: {e}")

    @commands.command(name='deauth', help='De-authenticate and remove Google account connection.')
    @commands.is_owner()
    async def deauth(self, ctx: commands.Context):
        """Deletes the token.json file, revoking access."""
        if os.path.exists("token.json"):
            os.remove("token.json")
            await ctx.send("✅ Successfully de-authenticated. I have forgotten your Google account connection.")
        else:
            await ctx.send("I am not currently authenticated. No action was taken.")

# =================================================================================
# Tools Cog (Calendar, Mail, and Ping)
# =================================================================================
class ToolsCog(commands.Cog):
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
            upcoming_events = await loop.run_in_executor(None, google_calendar.fetch_upcoming_events, 5)
            if not upcoming_events: return await thinking_message.edit(content="No upcoming events found.")
            await thinking_message.delete()
            for event in upcoming_events: await ctx.send(view=EventView(event))
        except Exception as e:
            await thinking_message.edit(content=f"An error occurred: `{e}`")

    @commands.command(name='mail', help='Shows your latest unread emails.')
    async def mail(self, ctx: commands.Context):
        thinking_message = await ctx.send("📧 Fetching unread mail...")
        loop = asyncio.get_running_loop()
        try:
            unread_emails = await loop.run_in_executor(None, google_gmail.fetch_unread_emails, 5)
            if not unread_emails: return await thinking_message.edit(content="No unread emails found!")
            await thinking_message.edit(content="**Here are your latest unread emails:**")
            for email in unread_emails: await ctx.send(view=MailDisplayView(email['subject'], email['sender']))
        except Exception as e:
            await thinking_message.edit(content=f"An error occurred: `{e}`")

# (The UI components like EventEditModal, EventView, and MailDisplayView are correct and unchanged)
# (I am including them here for absolute completeness)
class EventEditModal(discord.ui.Modal):
    def __init__(self,event:dict):
        super().__init__(title="Edit Calendar Event");self.event=event;s=event.get('summary','');d=event.get('description','');l=event.get('location','');ss,es="",""
        if 'dateTime' in event['start']:s_dt,e_dt=[datetime.datetime.fromisoformat(event[k]['dateTime']) for k in['start','end']];ss,es=s_dt.strftime('%Y-%m-%d %H:%M'),e_dt.strftime('%Y-%m-%d %H:%M')
        self.si,self.sti,self.ei,self.li,self.di=[discord.ui.TextInput(label=lbl,default=df,style=st,required=rq) for lbl,df,st,rq in[("Event Title",s,discord.TextStyle.short,True),("Start(YYYY-MM-DD HH:MM)",ss,discord.TextStyle.short,True),("End(YYYY-MM-DD HH:MM)",es,discord.TextStyle.short,True),("Location",l,discord.TextStyle.short,False),("Description",d,discord.TextStyle.paragraph,False)]]
        for i in[self.si,self.sti,self.ei,self.li,self.di]:self.add_item(i)
    async def on_submit(self,interaction:discord.Interaction):
        await interaction.response.defer(ephemeral=True,thinking=True)
        try:
            s_dt,e_dt=[datetime.datetime.strptime(i.value,'%Y-%m-%d %H:%M').astimezone() for i in[self.sti,self.ei]];s_iso,e_iso=s_dt.isoformat(),e_dt.isoformat()
            ue=await asyncio.get_running_loop().run_in_executor(None,google_calendar.update_event,self.event['id'],self.si.value,s_iso,e_iso,self.di.value,self.li.value)
            await interaction.followup.send("✅ Event updated!" if ue else "❌ Update failed.",ephemeral=True)
        except Exception as e:await interaction.followup.send(f"❌ Error: {e}",ephemeral=True)
class EventView(discord.ui.View):
    def __init__(self,event:dict):
        super().__init__(timeout=None);self.event=event;s,ts=event.get('summary','No Title'),"All-Day"
        if 'dateTime' in event['start']:s_dt,e_dt=[datetime.datetime.fromisoformat(event[k]['dateTime']) for k in['start','end']];ts=f"{s_dt.strftime('%-I:%M %p')} - {e_dt.strftime('%-I:%M %p')}"
        bl=f"{s}  |  {ts}";bl=(bl[:77]+'...') if len(bl)>80 else bl
        self.eb=discord.ui.Button(label=bl,style=discord.ButtonStyle.secondary,custom_id=f"edit_{event['id']}");self.eb.callback=self.button_callback;self.add_item(self.eb)
    async def button_callback(self,interaction:discord.Interaction):await interaction.response.send_modal(EventEditModal(self.event))
class MailDisplayView(discord.ui.View):
    def __init__(self,email_subject:str,email_sender:str):
        super().__init__(timeout=None);sn=email_sender.split('<')[0].strip().title().replace('"','');bl=f"{sn}: {email_subject}";bl=(bl[:77]+'...') if len(bl)>80 else bl
        self.add_item(discord.ui.Button(label=bl,style=discord.ButtonStyle.secondary,disabled=True))

# =================================================================================
# Core Bot Class and Execution
# =================================================================================
class AuraBot(commands.Bot):
    def __init__(self):
        intents=discord.Intents.default();intents.message_content,intents.members=True,True
        super().__init__(command_prefix='!',intents=intents)
    async def setup_hook(self):
        await self.add_cog(AuthCog(self));await self.add_cog(ToolsCog(self))
        print("Successfully loaded all cogs.")
    async def on_ready(self):
        print(f'Logged on as {self.user} ({self.user.id})');print('Aura is online and ready.');print('------')
    async def on_message(self,message:discord.Message):
        if message.author==self.user:return
        if self.user.mentioned_in(message) and not message.mention_everyone:
            async with message.channel.typing():
                prompt=message.content.replace(f'<@!{self.user.id}>','').replace(f'<@{self.user.id}>','').strip()
                response=await asyncio.get_running_loop().run_in_executor(None,agent_core.get_gemini_response,prompt)
                await message.reply(response)
            return
        await self.process_commands(message)

def run_bot():
    bot=AuraBot()
    if config.DISCORD_BOT_TOKEN:
        bot.run(config.DISCORD_BOT_TOKEN)
    else:
        print("CRITICAL ERROR: DISCORD_BOT_TOKEN not found.")