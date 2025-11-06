"""
Instagram Cog - Instagram Page Management
All Instagram commands and functionality
"""

import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
from datetime import datetime
import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import db
from utils.oauth import oauth
from utils.scheduler import scheduler
import config


class Instagram(commands.Cog):
    """Instagram commands for Discord bot"""
    
    def __init__(self, bot):
        self.bot = bot
        self.rate_limiter = RateLimiter()
        print('📸 Instagram cog initialized')

    async def cog_load(self):
        """Start OAuth server and scheduler when cog loads"""
        print(' Loading Instagram cog...')
        
        # Start OAuth server
        await oauth.start_server()
        
        # Setup scheduler
        scheduler.set_instagram_callback(self.publish_scheduled_post)
        scheduler.schedule_check(db)
        scheduler.start()
        
        print('✅ Instagram cog loaded successfully')

    # ---------------------------
    #  CONNECT / DISCONNECT
    # ---------------------------
    @app_commands.command(name="ig-connect", description="Connect your Instagram Account")
    async def connect(self, interaction: discord.Interaction):
        server_id = str(interaction.guild_id)

        existing = db.get_instagram_account(server_id)
        if existing:
            await interaction.response.send_message(
                f"✅ Already connected to **{existing.get('username', 'Instagram Account')}**!\nUse `/ig-disconnect` to reconnect.",
                ephemeral=True
            )
            return

        # Generate Instagram OAuth URL
        auth_url = oauth.get_instagram_auth_url(server_id)
        future = asyncio.Future()
        oauth.pending_auth[server_id] = future

        embed = discord.Embed(
            title="📸 Connect Instagram Account",
            description=f"**Step 1:** [Click here to authorize Instagram]({auth_url})\n\n**Step 2:** Allow permissions for posts and insights.\n⏱️ Link expires in 5 minutes",
            color=config.COLOR_INSTAGRAM
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        try:
            account_data = await asyncio.wait_for(future, timeout=300)
            db.save_instagram_account(server_id, account_data)

            success = discord.Embed(
                title="✅ Instagram Connected!",
                description=f"Connected as **{account_data['username']}**",
                color=config.COLOR_SUCCESS
            )
            success.add_field(
                name="📝 Commands",
                value="`/ig-post`, `/ig-schedule`, `/ig-recent`, `/ig-stats`, `/ig-delete`",
                inline=False
            )
            await interaction.followup.send(embed=success, ephemeral=True)
        except asyncio.TimeoutError:
            await interaction.followup.send("❌ Connection timed out. Try `/ig-connect` again.", ephemeral=True)
        finally:
            oauth.pending_auth.pop(server_id, None)

    @app_commands.command(name="ig-disconnect", description="Disconnect Instagram Account")
    async def disconnect(self, interaction: discord.Interaction):
        server_id = str(interaction.guild_id)
        account = db.get_instagram_account(server_id)

        if not account:
            await interaction.response.send_message("❌ No Instagram account connected.", ephemeral=True)
            return

        db.delete_instagram_account(server_id)
        await interaction.response.send_message(f"✅ Disconnected **{account['username']}**", ephemeral=True)

    # ---------------------------
    #  POST / IMAGE / SCHEDULE
    # ---------------------------
    @app_commands.command(name="ig-post", description="Post image to Instagram")
    @app_commands.describe(image_url="Public image URL", caption="Optional caption")
    async def post(self, interaction: discord.Interaction, image_url: str, caption: str = None):
        await interaction.response.defer()
        server_id = str(interaction.guild_id)
        account = db.get_instagram_account(server_id)

        if not account:
            await interaction.followup.send("❌ No Instagram account connected. Use `/ig-connect` first.")
            return

        try:
            await self.rate_limiter.wait()
            post_id = await self.post_photo(account['ig_user_id'], account['access_token'], image_url, caption)

            db.save_instagram_post({
                'server_id': server_id,
                'ig_user_id': account['ig_user_id'],
                'ig_post_id': post_id,
                'caption': caption,
                'image_url': image_url,
                'status': 'published',
                'platform': 'instagram'
            })

            embed = discord.Embed(
                title="✅ Posted to Instagram!",
                description=caption or "No caption",
                color=config.COLOR_SUCCESS
            )
            embed.set_image(url=image_url)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ Error posting: {str(e)}")

    @app_commands.command(name="ig-schedule", description="Schedule an Instagram post")
    @app_commands.describe(
        image_url="Public image URL",
        caption="Caption for the post",
        datetime_str="When to post (YYYY-MM-DD HH:MM UTC)"
    )
    async def schedule(self, interaction: discord.Interaction, image_url: str, caption: str, datetime_str: str):
        server_id = str(interaction.guild_id)
        account = db.get_instagram_account(server_id)

        if not account:
            await interaction.response.send_message("❌ No Instagram account connected.", ephemeral=True)
            return

        try:
            scheduled_at = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
            if scheduled_at <= datetime.utcnow():
                await interaction.response.send_message("❌ Must be a future date/time.", ephemeral=True)
                return

            post_id = db.save_instagram_post({
                'server_id': server_id,
                'ig_user_id': account['ig_user_id'],
                'image_url': image_url,
                'caption': caption,
                'scheduled_at': scheduled_at,
                'status': 'scheduled',
                'platform': 'instagram'
            })

            embed = discord.Embed(
                title="⏰ Post Scheduled",
                description=f"Will post on **{datetime_str} UTC**",
                color=config.COLOR_WARNING
            )
            embed.set_image(url=image_url)
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(f"❌ Scheduling error: {e}", ephemeral=True)

    # ---------------------------
    #  RECENT / STATS / DELETE
    # ---------------------------
    @app_commands.command(name="ig-recent", description="Show recent Instagram posts")
    async def recent(self, interaction: discord.Interaction):
        await interaction.response.defer()
        server_id = str(interaction.guild_id)
        account = db.get_instagram_account(server_id)

        if not account:
            await interaction.followup.send("❌ No Instagram account connected.")
            return

        try:
            await self.rate_limiter.wait()
            url = f"{config.INSTAGRAM_GRAPH_URL}/{account['ig_user_id']}/media"
            params = {'fields': 'id,caption,media_url,permalink,timestamp', 'access_token': account['access_token']}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    data = await resp.json()
                    posts = data.get('data', [])
                    if not posts:
                        await interaction.followup.send("📭 No posts found.")
                        return

                    embed = discord.Embed(
                        title=f"📸 Recent Instagram Posts ({len(posts)} found)",
                        color=config.COLOR_INSTAGRAM
                    )
                    for p in posts[:5]:
                        caption = p.get('caption', 'No caption')[:100]
                        embed.add_field(
                            name=f"🕓 {p['timestamp'][:10]}",
                            value=f"{caption}\n[View Post]({p['permalink']})",
                            inline=False
                        )
                    await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")

    @app_commands.command(name="ig-stats", description="Get stats for an Instagram post")
    @app_commands.describe(post_id="Instagram post ID")
    async def stats(self, interaction: discord.Interaction, post_id: str):
        await interaction.response.defer()
        server_id = str(interaction.guild_id)
        account = db.get_instagram_account(server_id)

        if not account:
            await interaction.followup.send("❌ No Instagram account connected.")
            return

        try:
            url = f"{config.INSTAGRAM_GRAPH_URL}/{post_id}/insights"
            params = {
                'metric': 'impressions,reach,engagement,saved',
                'access_token': account['access_token']
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    data = await resp.json()
                    metrics = {m['name']: m['values'][0]['value'] for m in data.get('data', [])}

                    embed = discord.Embed(
                        title="📊 Instagram Insights",
                        description=f"Post `{post_id}` statistics",
                        color=config.COLOR_INSTAGRAM
                    )
                    for k, v in metrics.items():
                        embed.add_field(name=k.title(), value=f"{v:,}", inline=True)
                    await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ Error fetching stats: {str(e)}")

    @app_commands.command(name="ig-delete", description="Delete an Instagram post")
    async def delete(self, interaction: discord.Interaction, post_id: str):
        await interaction.response.defer()
        server_id = str(interaction.guild_id)
        account = db.get_instagram_account(server_id)

        if not account:
            await interaction.followup.send("❌ No Instagram account connected.")
            return

        try:
            url = f"{config.INSTAGRAM_GRAPH_URL}/{post_id}"
            params = {'access_token': account['access_token']}

            async with aiohttp.ClientSession() as session:
                async with session.delete(url, params=params) as resp:
                    if resp.status == 200:
                        await interaction.followup.send(f"✅ Deleted post `{post_id}`")
                    else:
                        await interaction.followup.send(f"❌ Failed: {await resp.text()}")

        except Exception as e:
            await interaction.followup.send(f"❌ Error deleting post: {str(e)}")

    async def post_photo(self, ig_user_id, access_token, image_url, caption=None):
        """Helper to post image"""
        url = f"{config.INSTAGRAM_GRAPH_URL}/{ig_user_id}/media"
        params = {'image_url': image_url, 'caption': caption or '', 'access_token': access_token}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, params=params) as resp:
                if resp.status != 200:
                    raise Exception(await resp.text())
                data = await resp.json()
                creation_id = data['id']

        # Publish media
        publish_url = f"{config.INSTAGRAM_GRAPH_URL}/{ig_user_id}/media_publish"
        publish_params = {'creation_id': creation_id, 'access_token': access_token}

        async with aiohttp.ClientSession() as session:
            async with session.post(publish_url, params=publish_params) as resp:
                if resp.status != 200:
                    raise Exception(await resp.text())
                data = await resp.json()
                return data['id']

    async def publish_scheduled_post(self, post):
        """Publish scheduled Instagram post"""
        try:
            account = db.get_instagram_account(post['server_id'])
            if not account:
                db.update_instagram_post_status(post['_id'], 'failed')
                print(f"❌ No account found for server {post['server_id']}")
                return

            await self.rate_limiter.wait()
            post_id = await self.post_photo(account['ig_user_id'], account['access_token'], post['image_url'], post['caption'])
            db.update_instagram_post_status(post['_id'], 'published', post_id)
            print(f"✅ Published scheduled Instagram post: {post_id}")
        except Exception as e:
            print(f"❌ Failed to publish Instagram post: {e}")
            db.update_instagram_post_status(post['_id'], 'failed')


class RateLimiter:
    """Instagram API rate limiter"""
    def __init__(self):
        self.calls = []
        self.max_calls = config.INSTAGRAM_MAX_CALLS
        self.window = config.RATE_LIMIT_WINDOW

    async def wait(self):
        now = datetime.utcnow().timestamp()
        self.calls = [t for t in self.calls if t > now - self.window]
        if len(self.calls) >= self.max_calls:
            wait_time = self.calls[0] + self.window - now
            print(f'⏸️ Instagram rate limit reached, waiting {wait_time:.0f}s')
            await asyncio.sleep(wait_time)
            self.calls = []
        self.calls.append(now)


async def setup(bot):
    await bot.add_cog(Instagram(bot))
