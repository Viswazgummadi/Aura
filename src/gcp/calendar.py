# In src/gcp/calendar.py
import datetime
import os.path
import discord  # <-- Important: discord.py is used here now

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
TOKEN_PATH = "token.json"
CREDS_PATH = "credentials.json"

def get_calendar_service():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds = run_auth_flow()
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)

def run_auth_flow():
    if not os.path.exists(CREDS_PATH):
        raise FileNotFoundError(f"CRITICAL: '{CREDS_PATH}' not found.")
    flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
    creds = flow.run_local_server(port=0)
    return creds

def list_upcoming_events() -> discord.Embed:
    """
    Fetches the next 5 events and returns them as a rich Discord Embed.
    """
    try:
        service = get_calendar_service()
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=5,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        embed = discord.Embed(
            title="📅 Upcoming Calendar Events",
            color=discord.Color.from_rgb(66, 133, 244) # Google Blue
        )

        if not events:
            embed.description = "No upcoming events found."
            return embed

        for event in events:
            summary = event.get('summary', 'No Title')
            event_link = event.get('htmlLink', 'https://calendar.google.com')
            location = event.get('location', None)
            
            start = event['start']
            end = event['end']
            time_str = ""

            if 'dateTime' in start: # Timed event
                start_dt = datetime.datetime.fromisoformat(start['dateTime'])
                end_dt = datetime.datetime.fromisoformat(end['dateTime'])
                
                if start_dt.date() == end_dt.date():
                    time_str = f"**When:** {start_dt.strftime('%a, %b %d')} from `{start_dt.strftime('%-I:%M %p')}` to `{end_dt.strftime('%-I:%M %p')}`"
                else:
                    time_str = f"**From:** `{start_dt.strftime('%a, %b %d, %-I:%M %p')}`\n**To:** `{end_dt.strftime('%a, %b %d, %-I:%M %p')}`"
            
            else: # All-day event
                start_dt = datetime.datetime.strptime(start['date'], '%Y-%m-%d').date()
                end_dt = datetime.datetime.strptime(end['date'], '%Y-%m-%d').date()
                if (end_dt - start_dt).days == 1:
                    time_str = f"**When:** {start_dt.strftime('%a, %b %d')} (All-day)"
                else:
                    end_dt_inclusive = end_dt - datetime.timedelta(days=1)
                    time_str = f"**From:** `{start_dt.strftime('%a, %b %d')}` to `{end_dt_inclusive.strftime('%a, %b %d')}`"

            field_value = time_str
            if location:
                field_value += f"\n**Where:** `{location}`"

            embed.add_field(
                name=f"🗓️ {summary}",
                value=f"[Open in Google Calendar]({event_link})\n{field_value}",
                inline=False
            )

        embed.set_footer(text="Data from Google Calendar API")
        return embed

    except Exception as e:
        print(f"An error occurred in list_upcoming_events: {e}")
        error_embed = discord.Embed(
            title="Error Fetching Events",
            description="An error occurred while getting calendar data. Check the bot's console for details.",
            color=discord.Color.red()
        )
        return error_embed