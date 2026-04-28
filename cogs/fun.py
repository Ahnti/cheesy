from discord.ext import commands
import discord
import random
import aiohttp

class SbView(discord.ui.View):
    def __init__(self, images, tag):
        super().__init__(timeout=60)
        self.images = images
        self.tag = tag
        self.index = 0

    def build_embed(self):
        image_url= f"https://safebooru.org//images/{self.images[self.index]['directory']}/{self.images[self.index]['image']}"
        embed = discord.Embed(color=discord.Color.random())
        embed.set_image(url=image_url)
        embed.set_footer(text=f"tag: {self.tag} | {self.index + 1}/{len(self.images)}")
        return embed

    @discord.ui.button(label="<", style=discord.ButtonStyle.grey)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index - 1) % len(self.images)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label=">", style=discord.ButtonStyle.grey)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index + 1) % len(self.images)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ping", help="Approximately measures latency...", usage="ping")
    async def ping(self, ctx):
        ping = int(round(self.bot.latency*1000, -2))
        await ctx.send(f"Idk, {ping} something ms")

    @commands.command(name="hi", help="hi", usage="hi")
    async def hi(self, ctx):
        await ctx.send("hi")
       
    @commands.command(name="parrot", help="Parrots back what you say. Parrots back what you say.")
    async def parrot(self, ctx, *, message: str):
        await ctx.send(message)

    @commands.command(name="dm", help="Sends a dm to someone!", usage="@recipient [message]")
    async def dm(self, ctx, user: discord.User, *, message: str):
        try:
            await user.send(message)
            await ctx.send("pipe bomb sent")
        except discord.Forbidden:
            await ctx.send("tell them to let me in fiirsssttt.....")

    @commands.command(name="sb", help="Safebooru. Gets a random image.", usage="sb [tag]")
    async def sb(self, ctx, *, tag: str):
        url = f"https://safebooru.org/index.php?page=dapi&s=post&q=index&json=1&tags={tag}&limit=100"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    await ctx.send("asjdasdhajshd")
                    return

                data = await resp.json(content_type=None)

                if not data:
                    await ctx.send("too niche man")
                    return

                view = SbView(data, tag)
                await ctx.send(embed=view.build_embed(), view=view)
async def setup(bot):
    await bot.add_cog(Fun(bot))
