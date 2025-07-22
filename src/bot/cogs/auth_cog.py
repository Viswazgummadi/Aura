# File: src/bot/cogs/auth_cog.py (Standard Local Server Flow)

import discord
import asyncio
import os
from discord.ext import commands
from discord.ext.commands import Bot

from src.core import gcp_auth

class AuthCog(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(name='auth', help='Authenticate with your Google account.')
    @commands.is_owner()
    async def auth(self, ctx: commands.Context):
        """Starts the Google authentication process."""
        try:
            await ctx.author.send(
                "Starting Google authentication...\n\n"
                "A URL will be printed in the bot's console. You **must** open this URL "
                "in a browser **on the same computer the bot is running on**."
            )
            await ctx.message.add_reaction('✅')

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, gcp_auth.run_auth_flow)
            
            embed = discord.Embed(
                title="✅ Authentication Successful",
                description="I am now connected to your Google account. You can use the other commands now.",
                color=discord.Color.green()
            )
            await ctx.author.send(embed=embed)
        except Exception as e:
            await ctx.author.send(f"An error occurred during authentication: {e}")
            await ctx.message.add_reaction('❌')

    @commands.command(name='deauth', help='De-authenticate.')
    @commands.is_owner()
    async def deauth(self, ctx: commands.Context):
        if os.path.exists("token.json"):
            os.remove("token.json")
            await ctx.send("✅ Successfully de-authenticated.")
        else:
            await ctx.send("I am not currently authenticated.")

async def setup(bot: Bot):
    await bot.add_cog(AuthCog(bot))