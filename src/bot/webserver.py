# File: src/bot/webserver.py

import json
import base64
import threading
from flask import Flask, request, jsonify
import asyncio
from functools import partial

from src.agent.tools import gmail as gmail_tool
import gmail_history_tracker
from src.core import config 
from gmail_history_tracker import GMAIL_PROCESSING_LOCK # <-- IMPORT THE LOCK

discord_bot_instance = None 

app = Flask(__name__)

@app.route('/', methods=['POST'])
def gmail_webhook():
    if request.method == 'POST':
        try:
            envelope = request.get_json()
            if not envelope or 'message' not in envelope:
                print("WEBHOOK ERROR: Invalid Pub/Sub message format.")
                return 'Invalid Pub/Sub message format', 400

            pubsub_message_data = base64.b64decode(envelope['message']['data']).decode('utf-8')
            pubsub_message = json.loads(pubsub_message_data)

            email_address = pubsub_message.get('emailAddress')
            webhook_history_id = int(pubsub_message.get('historyId'))

            print(f"WEBHOOK: Received notification for {email_address}, historyId: {webhook_history_id}. Queuing task.")

            if discord_bot_instance and discord_bot_instance.loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    process_gmail_notification_async(email_address, webhook_history_id),
                    discord_bot_instance.loop
                )
            else:
                print("WEBHOOK WARNING: Discord bot event loop not running. Skipping.")

            return '', 204

        except Exception as e:
            print(f"WEBHOOK CRITICAL ERROR: {e}")
            return 'Error', 500
    return 'Method not allowed', 405


async def process_gmail_notification_async(email_address: str, webhook_history_id: int):
    async with GMAIL_PROCESSING_LOCK: # <-- ACQUIRE THE LOCK
        print(f"\n--- [LOCKED] Processing webhook for {email_address} (ID: {webhook_history_id}) ---")
        try:
            last_processed_id = gmail_history_tracker.get_last_history_id()
            
            if last_processed_id and webhook_history_id <= last_processed_id:
                print(f"PROCESS: Webhook ID ({webhook_history_id}) is not newer than tracker ({last_processed_id}). Skipping.")
                print("--- [UNLOCKED] Processing complete (redundant) ---\n")
                return

            messages, new_history_id = await discord_bot_instance.loop.run_in_executor(
                None, gmail_tool.fetch_new_messages_for_processing_from_api, last_processed_id
            )

            if messages:
                print(f"PROCESS: Found {len(messages)} new messages to notify.")
                owner = discord_bot_instance.get_user(config.DISCORD_OWNER_ID)
                
                if owner:
                    for msg in messages:
                        await owner.send(f"📧 New Mail: **{msg['subject']}** from **{msg['sender'].split('<')[0].strip()}**")
                        await discord_bot_instance.loop.run_in_executor(None, gmail_tool.mark_message_as_read, msg['id'])
                        gmail_history_tracker.add_processed_message_id(msg['id'])
                    
                    gmail_history_tracker.set_last_history_id(new_history_id)
                else:
                    print("PROCESS WARNING: Owner not found, cannot send DMs.")
            else:
                print("PROCESS: No new messages found. Advancing history tracker.")
                current_api_history = await discord_bot_instance.loop.run_in_executor(None, gmail_tool.get_latest_history_id_from_gmail_api)
                if current_api_history > (last_processed_id or 0):
                     gmail_history_tracker.set_last_history_id(current_api_history)

        except Exception as e:
            print(f"PROCESS ERROR: {e}")
        
        print("--- [UNLOCKED] Processing complete ---\n")


def run_webserver(bot_instance, host='0.0.0.0', port=5000):
    global discord_bot_instance
    discord_bot_instance = bot_instance

    def _run():
        app.run(host=host, port=port)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    print(f"Flask web server started on http://{host}:{port}")