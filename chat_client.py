# File: chat_client.py
import asyncio
import websockets
import json
import uuid

# --- CONFIGURATION ---
# The test script will tell you which token to paste here.
JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbkBhdXJhLnRlc3QiLCJ1c2VyX2lkIjoxLCJleHAiOjE3NTQwNzIyMDZ9.6h3-Qh155h4ITYY1xUUW6CANEEccaVDH4zm2ySqGje4"
# ---------------------
    
SESSION_ID = str(uuid.uuid4())
WEBSOCKET_URI = f"ws://localhost:8000/agent/ws/{SESSION_ID}"
HEADERS = {"Authorization": f"Bearer {JWT_TOKEN}"}

async def run_chat_client():
    """
    A simple command-line client to interact with the Aura agent's WebSocket endpoint.
    """
    print("--- Aura Command-Line Client ---")
    print(f"Connecting to: {WEBSOCKET_URI}")
    print(f"Session ID: {SESSION_ID}")
    print("Type 'exit' to quit.")
    print("---------------------------------")

    if "YOUR_JWT_HERE" in JWT_TOKEN:
        print("\n🚨 ERROR: Please edit this file and replace 'YOUR_JWT_HERE' with a valid token.\n")
        return

    try:
        # Attempt to connect to the WebSocket server with our auth headers.
        async with websockets.connect(WEBSOCKET_URI, extra_headers=HEADERS) as websocket:
            print("✅ Connection successful!")

            async def receive_messages():
                """A background task to listen for incoming messages and print them."""
                try:
                    async for message in websocket:
                        data = json.loads(message)
                        if data.get("type") == "token_chunk":
                            # Print the LLM's streamed tokens as they arrive.
                            print(data.get("content", ""), end="", flush=True)
                        elif data.get("type") == "tool_start":
                            # Announce that the agent is using a tool.
                            print(f"\n\n🤖 Thinking... (Using tool: {data['tool_name']})", flush=True)
                        elif data.get("type") == "error":
                            # Print any errors sent by the server.
                            print(f"\n\n❌ Server Error: {data['content']}", flush=True)
                except websockets.exceptions.ConnectionClosed:
                    print("\nConnection to server lost.")

            # Start the background task that listens for server messages.
            receive_task = asyncio.create_task(receive_messages())

            # Loop to get input from the user.
            while True:
                user_input = await asyncio.to_thread(input, "\n\n> ")
                if user_input.lower() == 'exit':
                    break
                
                # Send the user's message over the WebSocket to the server.
                await websocket.send(user_input)
            
            # Clean up the background task when the user exits.
            receive_task.cancel()

    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ Connection failed: HTTP Status {e.status_code}")
        print("   - Is your JWT token correct and not expired?")
        print("   - Is your FastAPI server running?")
    except ConnectionRefusedError:
        print("❌ Connection failed: Connection refused.")
        print("   - Is your FastAPI server running on http://localhost:8000?")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(run_chat_client())