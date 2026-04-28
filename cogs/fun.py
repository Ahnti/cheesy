from discord.ext import commands
import discord
import random

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='ping')
    async def ping(self, ctx):
        ping = int(round(self.bot.latency*1000, -2))
        await ctx.send(f"Idk, {ping} something ms")

async def setup(bot):
    await bot.add_cog(Fun(bot))
