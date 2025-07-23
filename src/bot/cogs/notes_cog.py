# File: src/bot/cogs/notes_cog.py

import discord
from discord.ext import commands
from discord.ext.commands import Bot

# Import the functions from our new notes tool
from src.agent.tools import notes as notes_tool

class NotesCog(commands.Cog):
    """
    A cog for commands related to personal information management (notes).
    """
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(name='save', help='Saves a piece of information.')
    @commands.is_owner()
    async def save_note(self, ctx: commands.Context, key: str, value: str):
        """
        Saves a value under a specific key.
        Usage: !save "wifi password" "MyPassword123"
        """
        try:
            notes_tool.save_note(key, value)
            embed = discord.Embed(
                title="✅ Note Saved",
                description=f"I will remember that **`{key}`** is **`{value}`**.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ An error occurred while saving the note: {e}")

    @commands.command(name='get', help='Retrieves a piece of information.')
    @commands.is_owner()
    async def get_note(self, ctx: commands.Context, key: str):
        """
        Gets the value for a specific key.
        Usage: !get "wifi password"
        """
        try:
            value = notes_tool.get_note(key)
            if value:
                embed = discord.Embed(
                    title=f"📝 Note for '{key}'",
                    description=f"**`{value}`**",
                    color=discord.Color.blue()
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"🤔 I don't have a note with the key **`{key}`**.")
        except Exception as e:
            await ctx.send(f"❌ An error occurred while getting the note: {e}")

    @commands.command(name='notes', help='Lists all saved notes.')
    @commands.is_owner()
    async def list_notes(self, ctx: commands.Context):
        """
        Displays all saved key-value notes.
        """
        try:
            all_notes = notes_tool.list_notes()
            if not all_notes:
                await ctx.send("You haven't saved any notes yet.")
                return

            embed = discord.Embed(
                title="🗒️ Your Saved Notes",
                color=discord.Color.orange()
            )
            
            notes_str = ""
            for key, data in all_notes.items():
                notes_str += f"**`{key}`** : `{data['value']}`\n"
            
            embed.description = notes_str
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ An error occurred while listing notes: {e}")

    @commands.command(name='delnote', help='Deletes a saved note.')
    @commands.is_owner()
    async def delete_note(self, ctx: commands.Context,  key: str):
        """
        Deletes a note by its key.
        Usage: !delnote "wifi password"
        """
        try:
            if notes_tool.delete_note(key):
                embed = discord.Embed(
                    title="🗑️ Note Deleted",
                    description=f"I have forgotten the note for **`{key}`**.",
                    color=discord.Color.dark_gray()
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"🤔 Could not find a note with the key **`{key}`** to delete.")
        except Exception as e:
            await ctx.send(f"❌ An error occurred while deleting the note: {e}")

async def setup(bot: Bot):
    """This special function is called by discord.py when loading a cog."""
    await bot.add_cog(NotesCog(bot))