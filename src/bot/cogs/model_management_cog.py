# File: src/bot/cogs/model_management_cog.py

import discord
from discord.ext import commands
from discord.ext.commands import Bot

# Import our new manager and the core LLM loader
from src.core import model_manager
from src.agent import core as agent_core

class ModelManagementCog(commands.Cog):
    """
    A cog for managing different LLM models and API keys.
    """
    def __init__(self, bot: Bot):
        self.bot = bot

    # --- API Key Management ---
    
    @commands.command(name='addkey', help='Adds or updates an API key.')
    @commands.is_owner()
    async def add_key(self, ctx: commands.Context, key_name: str, key_value: str):
        """Usage: !addkey <key_name> <api_key_value>"""
        try:
            model_manager.add_api_key(key_name, key_value)
            await ctx.send(f"✅ API Key '{key_name}' has been saved.")
        except Exception as e:
            await ctx.send(f"❌ Error saving key: {e}")

    @commands.command(name='delkey', help='Deletes an API key.')
    @commands.is_owner()
    async def del_key(self, ctx: commands.Context, key_name: str):
        """Usage: !delkey <key_name>"""
        try:
            if model_manager.remove_api_key(key_name):
                await ctx.send(f"✅ API Key '{key_name}' has been deleted.")
            else:
                await ctx.send(f"🤔 API Key '{key_name}' not found.")
        except Exception as e:
            await ctx.send(f"❌ Error deleting key: {e}")

    @commands.command(name='keys', help='Lists all saved API key names.')
    @commands.is_owner()
    async def list_keys(self, ctx: commands.Context):
        keys = model_manager.list_api_keys()
        if not keys:
            return await ctx.send("No API keys have been saved.")
        
        embed = discord.Embed(title="🔑 Saved API Keys", color=discord.Color.orange())
        key_list = "\n".join([f"`{name}`" for name in keys.keys()])
        embed.description = key_list
        await ctx.send(embed=embed)

    # --- Model Management ---

    @commands.command(name='addmodel', help='Adds a new model configuration.')
    @commands.is_owner()
    async def add_model(self, ctx: commands.Context, model_id: str, model_name: str, provider: str, key_name: str):
        """Usage: !addmodel <id> <model_name> <provider> <key_name>"""
        try:
            model_manager.add_model(model_id, model_name, provider, key_name)
            await ctx.send(f"✅ Model '{model_id}' has been added.")
        except Exception as e:
            await ctx.send(f"❌ Error adding model: {e}")

    @commands.command(name='delmodel', help='Deletes a model configuration.')
    @commands.is_owner()
    async def del_model(self, ctx: commands.Context, model_id: str):
        """Usage: !delmodel <model_id>"""
        try:
            if model_manager.remove_model(model_id):
                await ctx.send(f"✅ Model '{model_id}' has been deleted.")
            else:
                await ctx.send(f"🤔 Model '{model_id}' not found.")
        except Exception as e:
            await ctx.send(f"❌ Error deleting model: {e}")

    @commands.command(name='models', help='Lists all available models.')
    @commands.is_owner()
    async def list_models(self, ctx: commands.Context):
        models = model_manager.list_models()
        if not models:
            return await ctx.send("No models have been configured.")
            
        embed = discord.Embed(title="🤖 Available Models", color=discord.Color.blue())
        for model_id, details in models.items():
            embed.add_field(
                name=f"`{model_id}`",
                value=f"**Name:** {details['model_name']}\n"
                      f"**Provider:** {details['provider']}\n"
                      f"**Key:** {details['api_key_id']}",
                inline=False
            )
        await ctx.send(embed=embed)

    # --- Active Model Control ---

    @commands.command(name='usemodel', help='Sets the active model and reloads the agent.')
    @commands.is_owner()
    async def use_model(self, ctx: commands.Context, model_id: str):
        """Usage: !usemodel <model_id>"""
        try:
            model_manager.set_active_model(model_id)
            await ctx.send(f"🧠 Set active model to `{model_id}`. Reloading agent core...")
            
            # This is the crucial part: we call the function to reload the model.
            agent_core.create_llm_instance()
            
            # We need to re-compile the graph with the new model instance
            # This is an advanced step, for now we will just reload the instance
            # and the next agent call will use it. A full reload is more complex.
            
            await ctx.send("✅ Agent core reloaded. Now using new model.")
        except Exception as e:
            await ctx.send(f"❌ Error setting active model: {e}")

    @commands.command(name='currentmodel', help='Shows the currently active model.')
    @commands.is_owner()
    async def current_model(self, ctx: commands.Context):
        active_config = model_manager.get_active_config()
        if not active_config:
            return await ctx.send("No active model is set.")
        
        embed = discord.Embed(title="⚡ Active Model", color=discord.Color.green())
        embed.add_field(name="Model Name", value=active_config['model_name'])
        embed.add_field(name="API Key In Use", value="********") # Obscure the key for safety
        await ctx.send(embed=embed)


async def setup(bot: Bot):
    """This special function is called by discord.py when loading a cog."""
    await bot.add_cog(ModelManagementCog(bot))