# Aura AI Assistant Bot

Aura is a personal AI assistant for Discord, capable of integrating with your Google Calendar and Gmail.

## Features

-   Chat with a Gemini-powered AI by mentioning the bot.
-   View and edit your upcoming Google Calendar events.
-   View your latest unread emails.
-   Secure, user-controlled authentication.

## Setup Instructions for Your Own Bot

Follow these steps to run your own personal instance of Aura.

### Prerequisites

-   Python 3.10 or newer
-   A Discord account
-   A Google Cloud account

### 1. Set Up Your Discord Bot

1.  Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2.  Create a **New Application**.
3.  Go to the **"Bot"** tab and click **"Add Bot"**.
4.  **Enable Privileged Gateway Intents:** Turn ON `MESSAGE CONTENT INTENT` and `SERVER MEMBERS INTENT`.
5.  Click **"Reset Token"** to reveal your bot's token. **Copy this token.**

### 2. Set Up Your Google Cloud Project

1.  Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a **New Project**.
2.  **Enable APIs:** In your new project, enable the **Google Calendar API** and the **Gmail API**.
3.  **Configure OAuth Consent Screen:**
    -   Go to **APIs & Services -> OAuth consent screen**.
    -   Choose **External** user type.
    -   Fill in the required fields (App name, User support email, Developer contact).
    -   **Add Test Users:** Add your own Google email address as a test user.
4.  **Create Credentials:**
    -   Go to **APIs & Services -> Credentials**.
    -   Click **+ CREATE CREDENTIALS -> OAuth client ID**.
    -   Select **Desktop app** as the application type.
    -   After creation, **DOWNLOAD JSON**.

### 3. Set Up the Project Locally

1.  Clone this repository:
    ```bash
    git clone https://github.com/your-username/aura.git
    cd aura
    ```
2.  Create and activate a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```
3.  Install the required packages:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure Your Secrets:**
    -   Rename the downloaded Google credential file to `credentials.json` and place it in the project's root folder.
    -   Create a new file named `.env` in the root folder.
    -   Add your secrets to the `.env` file like this:
      ```env
      DISCORD_BOT_TOKEN="your-discord-bot-token-here"
      GOOGLE_API_KEY="your-gemini-api-key-here"
      ```

### 4. Run the Bot

1.  Run the bot from your terminal:
    ```bash
    python main.py
    ```
2.  Invite your bot to your server using the URL Generator in the Discord Developer Portal (OAuth2 section).
3.  In your Discord server, run the `!auth` command and follow the instructions in the console to connect your Google account.
