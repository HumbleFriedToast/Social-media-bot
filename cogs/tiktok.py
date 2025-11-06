from discord.ext import commands

class TikTokCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def tt_test(self, ctx):
        await ctx.send("TikTok cog fonctionne !")

async def setup(bot):
    await bot.add_cog(TikTokCog(bot))
