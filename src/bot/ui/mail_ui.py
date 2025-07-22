# File: src/bot/ui/mail_ui.py

import discord

class MailDisplayView(discord.ui.View):
    """
    A simple View that displays an email subject and sender on a disabled button.
    """
    def __init__(self, email_subject: str, email_sender: str):
        super().__init__(timeout=None)
        
        # Clean up the sender name for better display
        sender_name = email_sender.split('<')[0].strip().title().replace('"', '')
        
        # Create the button label
        button_label = f"{sender_name}: {email_subject}"
        
        # Truncate the label if it's too long for a Discord button
        if len(button_label) > 80:
            button_label = button_label[:77] + '...'
        
        self.add_item(discord.ui.Button(label=button_label, style=discord.ButtonStyle.secondary, disabled=True))