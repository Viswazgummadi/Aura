# File: src/bot/webserver.py

import json
import base64
import threading
from flask import Flask, request, jsonify
import asyncio
import time
from functools import partial

from src.agent.tools import gmail as gmail_tool
import gmail_history_tracker
from src.core import config 


discord_bot_instance = None 

# --- FLASK APP SETUP ---
app = Flask(__name__)

# --- WEBHOOK ENDPOINT ---
@app.route('/', methods=['POST'])
def gmail_webhook():
    if request.method == 'POST':
        try:
            envelope = request.get_json()
            if not envelope or not 'message' in envelope:
                print("WEBHOOK ERROR: Invalid Pub/Sub message format (missing 'message').")
                return jsonify({'status': 'error', 'message': 'Invalid Pub/Sub message format'}), 400

            pubsub_message_data = base64.b64decode(envelope['message']['data']).decode('utf-8')
            pubsub_message = json.loads(pubsub_message_data)

            email_address = pubsub_message.get('emailAddress')
            webhook_history_id = int(pubsub_message.get('historyId'))

            print(f"WEBHOOK: Received Gmail notification for {email_address}, webhook_historyId: {webhook_history_id}")

            if discord_bot_instance and discord_bot_instance.loop and discord_bot_instance.loop.is_running():
                discord_bot_instance.loop.call_soon_threadsafe(
                    partial(asyncio.ensure_future,
                            process_gmail_notification_async(email_address, webhook_history_id),
                            loop=discord_bot_instance.loop
                           )
                )
                print("WEBHOOK: Successfully queued Gmail processing task.")
            else:
                print("WEBHOOK WARNING: Discord bot event loop not yet running or available to process notification. Skipping.")

            return jsonify({'status': 'success'}), 200

        except Exception as e:
            print(f"WEBHOOK ERROR: {e}")
            if discord_bot_instance and config.DISCORD_OWNER_ID:
                owner = discord_bot_instance.get_user(config.DISCORD_OWNER_ID)
                if owner:
                    discord_bot_instance.loop.call_soon_threadsafe(
                        partial(asyncio.ensure_future,
                                owner.send(f"❌ Critical WEBHOOK ERROR: {str(e)}. Check bot console."),
                                loop=discord_bot_instance.loop
                               )
                    )
            return jsonify({'status': 'error', 'message': str(e)}), 500
    return jsonify({'status': 'method not allowed'}), 405


async def process_gmail_notification_async(email_address: str, webhook_history_id: int):
    print(f"DISCORD_BOT: Triggered to process Gmail for {email_address} (webhook: {webhook_history_id}).")
    
    if not gmail_history_tracker.get_current_email_address():
        print("DISCORD_BOT WARNING: Tracker's email address not set during startup. Attempting to set now from webhook context.")
        try:
            service = await discord_bot_instance.loop.run_in_executor(None, gmail_tool.build_google_service, 'gmail', 'v1')
            profile = await discord_bot_instance.loop.run_in_executor(None, service.users().getProfile(userId='me').execute)
            gmail_history_tracker.set_current_email_address(profile.get('emailAddress'))
            print(f"DEBUG: Set tracker email address dynamically to: {profile.get('emailAddress')}")
        except Exception as e:
            print(f"ERROR: Could not dynamically set email address in tracker from webhook context: {e}. Messages might be skipped.")

    last_processed_id_from_tracker = gmail_history_tracker.get_last_history_id()
    
    if last_processed_id_from_tracker is not None and webhook_history_id <= last_processed_id_from_tracker:
        print(f"DISCORD_BOT: Webhook historyId ({webhook_history_id}) is NOT strictly newer than last processed ({last_processed_id_from_tracker}). Skipping processing to prevent duplicates from old/redundant webhooks.")
        current_api_history = gmail_tool.get_latest_history_id_from_gmail_api()
        if current_api_history > (last_processed_id_from_tracker or 0):
            gmail_history_tracker.set_last_history_id(current_api_history)
            print(f"DISCORD_BOT: Tracker advanced to current Gmail API history: {current_api_history} (skipped webhook, but advanced tracker).")
        else:
            print(f"DISCORD_BOT: Tracker already up-to-date ({last_processed_id_from_tracker}). No action needed for this redundant webhook.")
        return

    try:
        messages_for_processing, new_history_id_from_fetch = await discord_bot_instance.loop.run_in_executor(
            None, gmail_tool.fetch_new_messages_for_processing_from_api, last_processed_id_from_tracker
        )

        if messages_for_processing:
            print(f"DISCORD_BOT: Found {len(messages_for_processing)} unique new messages to notify.")
            owner = discord_bot_instance.get_user(config.DISCORD_OWNER_ID)
            
            if owner:
                for msg in messages_for_processing:
                    await owner.send(
                        f"📧 New Mail: **{msg['subject']}** from **{msg['sender'].split('<')[0].strip()}**"
                        f" (ID: `{msg['id']}`)"
                    )
                    await discord_bot_instance.loop.run_in_executor(None, gmail_tool.mark_message_as_read, msg['id'])
                    gmail_history_tracker.add_processed_message_id(msg['id'])
                    print(f"DISCORD_BOT: Notified owner about new email and marked as read/processed: {msg['subject']}")
                
                final_history_id_to_save = max(new_history_id_from_fetch, webhook_history_id)
                gmail_history_tracker.set_last_history_id(final_history_id_to_save)
                print(f"DISCORD_BOT: History tracker updated to {final_history_id_to_save}")
            else:
                print("DISCORD_BOT WARNING: Owner user object not found, cannot send DM for new mails.")
        else:
            print(f"DISCORD_BOT: No truly new unique messages found in this processing cycle.")
            current_api_history = gmail_tool.get_latest_history_id_from_gmail_api()
            tracker_history = gmail_history_tracker.get_last_history_id() or 0
            if current_api_history > tracker_history:
                gmail_history_tracker.set_last_history_id(current_api_history)
                print(f"DISCORD_BOT: History tracker updated to current Gmail API history: {current_api_history} (no new messages found in range).")
            else:
                print(f"DISCORD_BOT: History tracker already up-to-date ({tracker_history}). No update needed from this webhook for range.")

    except Exception as e:
        print(f"DISCORD_BOT ERROR during Gmail processing: {e}")
        owner = discord_bot_instance.get_user(config.DISCORD_OWNER_ID)
        if owner:
            asyncio.run_coroutine_threadsafe(
                asyncio.create_task(owner.send(f"❌ Error processing Gmail notification: `{e}`. History NOT updated.")),
                discord_bot_instance.loop
            )
        # Do NOT update history on error, so it retries from same point next time


# --- FUNCTION TO START THE WEBSERVER ---
def run_webserver(bot_instance, host='0.0.0.0', port=5000):
    global discord_bot_instance
    discord_bot_instance = bot_instance

    def _run():
        app.run(host=host, port=port)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    print(f"Flask web server started on http://{host}:{port}")