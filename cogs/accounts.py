from discord.ext import commands

connected_accounts = {}  

class AccountCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def connect(self, ctx, platform):
        url = f"https://example.com/oauth/{platform.lower()}"  # URL fictive
        if ctx.guild.id not in connected_accounts:
            connected_accounts[ctx.guild.id] = []
        if platform.lower() not in connected_accounts[ctx.guild.id]:
            connected_accounts[ctx.guild.id].append(platform.lower())
        await ctx.send(f"Connecte ton compte {platform} ici : {url}")

    @commands.command()
    async def disconnect(self, ctx, platform):
        if ctx.guild.id in connected_accounts and platform.lower() in connected_accounts[ctx.guild.id]:
            connected_accounts[ctx.guild.id].remove(platform.lower())
            await ctx.send(f"Compte {platform} déconnecté.")
        else:
            await ctx.send(f"Aucun compte {platform} connecté.")

    @commands.command()
    async def accounts(self, ctx):
        accounts = connected_accounts.get(ctx.guild.id, [])
        if accounts:
            await ctx.send("Comptes connectés : " + ", ".join(accounts))
        else:
            await ctx.send("Aucun compte connecté.")

# ⚠️ NE PAS appeler bot.add_cog directement
# ⚠️ Utiliser setup async pour discord.py ≥ 2.0
async def setup(bot):
    await bot.add_cog(AccountCog(bot))
