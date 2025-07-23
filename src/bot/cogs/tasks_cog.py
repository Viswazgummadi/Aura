# File: src/bot/cogs/tasks_cog.py

import discord
from discord.ext import commands
from discord.ext.commands import Bot

# Import the functions from our new tasks tool
from src.agent.tools import tasks as tasks_tool

class TasksCog(commands.Cog):
    """
    A cog for commands related to personal task management.
    """
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(name='addtask', help='Adds a new task to your to-do list.')
    @commands.is_owner()
    async def add_task(self, ctx: commands.Context, *, description: str):
        """
        Adds a new task. The description is everything after the command.
        Usage: !addtask Write the project proposal
        """
        try:
            new_task = tasks_tool.add_task(description)
            embed = discord.Embed(
                title="✅ Task Added",
                description=f"**{new_task['description']}**",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"ID: {new_task['id']}")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ An error occurred while adding the task: {e}")

    @commands.command(name='tasks', help='Lists your pending tasks.')
    @commands.is_owner()
    async def list_tasks(self, ctx: commands.Context):
        """
        Displays a list of all tasks that are currently pending.
        """
        try:
            pending_tasks = tasks_tool.list_tasks(status_filter='pending')
            if not pending_tasks:
                await ctx.send("🎉 You have no pending tasks!")
                return

            embed = discord.Embed(
                title="📝 Your Pending Tasks",
                color=discord.Color.blue()
            )
            
            # Format the list of tasks
            task_list_str = ""
            for task in pending_tasks:
                task_list_str += f"`{task['id']}` - {task['description']}\n"
            
            embed.description = task_list_str
            embed.set_footer(text="Use !donetask <ID> to complete a task.")
            
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ An error occurred while listing tasks: {e}")

    @commands.command(name='donetask', help='Marks a task as complete.')
    @commands.is_owner()
    async def done_task(self, ctx: commands.Context, task_id: str):
        """
        Marks a specific task as complete using its ID.
        Usage: !donetask <task_id>
        """
        try:
            completed_task = tasks_tool.mark_task_complete(task_id)
            if completed_task:
                embed = discord.Embed(
                    title="🎉 Task Completed!",
                    description=f"~~{completed_task['description']}~~",
                    color=discord.Color.dark_gray()
                )
                embed.set_footer(text=f"ID: {completed_task['id']}")
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"🤔 Could not find a task with ID `{task_id}`.")
        except Exception as e:
            await ctx.send(f"❌ An error occurred while completing the task: {e}")


async def setup(bot: Bot):
    """This special function is called by discord.py when loading a cog."""
    await bot.add_cog(TasksCog(bot))