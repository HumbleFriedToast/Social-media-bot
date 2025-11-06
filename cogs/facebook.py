"""
Facebook Cog - Facebook Page Management
All Facebook commands and functionality
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


class Facebook(commands.Cog):
    """Facebook Page commands for Discord bot"""
    
    def __init__(self, bot):
        self.bot = bot
        self.rate_limiter = RateLimiter()
        print(' Facebook cog initialized')
    





    async def cog_load(self):
        """Start OAuth server and scheduler when cog loads"""
        print(' Loading Facebook cog...')
        
        # Start OAuth server
        await oauth.start_server()
        
        # Setup scheduler
        scheduler.set_facebook_callback(self.publish_scheduled_post)
        scheduler.schedule_check(db)
        scheduler.start()
        
        print('✅ Facebook cog loaded successfully')
    
    @app_commands.command(name="fb-connect", description="Connect your Facebook Page")





    async def connect(self, interaction: discord.Interaction):
        """Connect Facebook Page via OAuth"""
        server_id = str(interaction.guild_id)
        
        # Check if already connected
        existing = db.get_facebook_account(server_id)
        if existing:
            await interaction.response.send_message(
                f"✅ Already connected to **{existing.get('page_name', 'Facebook Page')}**!\nUse `/fb-disconnect` to reconnect.",
                ephemeral=True
            )
            return
        
        # Generate OAuth URL
        auth_url = oauth.get_auth_url(server_id)
        
        # Create future for waiting
        future = asyncio.Future()
        oauth.pending_auth[server_id] = future
        
        # Send link
        embed = discord.Embed(
            title=" Connect Facebook Page",
            description=f"**Step 1:** [Click here to authorize Facebook]({auth_url})\n\n**Step 2:** Select the page you want to connect\n\n⏱️ Link expires in 5 minutes",
            color=config.COLOR_FACEBOOK
        )
        embed.add_field(
            name="✅ Requirements",
            value="• Facebook account\n• Admin access to a Facebook Page\n• Page with posts enabled",
            inline=False
        )
        embed.set_footer(text="After authorizing, return to Discord")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Wait for OAuth callback
        try:
            pages_data = await asyncio.wait_for(future, timeout=300)
            pages = pages_data.get('data', [])
            
            if not pages:
                await interaction.followup.send(
                    "❌ No Facebook Pages found.\n\nMake sure:\n• You're an admin of at least one page\n• The page has posting permissions",
                    ephemeral=True
                )
                return
            
            # Use first page (or implement page selection logic)
            selected_page = pages[0]
            
            # If multiple pages, show info
            if len(pages) > 1:
                page_list = "\n".join([f"• {p['name']}" for p in pages[:5]])
                info_msg = f"Found {len(pages)} pages. Connected to: **{selected_page['name']}**\n\nOther pages:\n{page_list}"
            else:
                info_msg = f"Connected to: **{selected_page['name']}**"
            
            # Save page account
            db.save_facebook_account(server_id, {
                'page_id': selected_page['id'],
                'page_name': selected_page['name'],
                'access_token': selected_page['access_token']
            })
            
            success_embed = discord.Embed(
                title="✅ Facebook Page Connected!",
                description=info_msg,
                color=config.COLOR_SUCCESS
            )
            success_embed.add_field(
                name="📝 Available Commands",
                value="`/fb-post` - Post text/link\n`/fb-post-image` - Post image\n`/fb-schedule` - Schedule post\n`/fb-recent` - View recent posts\n`/fb-stats` - Get analytics",
                inline=False
            )
            
            await interaction.followup.send(embed=success_embed, ephemeral=True)
            
        except asyncio.TimeoutError:
            await interaction.followup.send(
                "❌ Connection timed out after 5 minutes.\n\nPlease try `/fb-connect` again.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Connection error: {str(e)}\n\nPlease try again or contact support.",
                ephemeral=True
            )
        finally:
            oauth.pending_auth.pop(server_id, None)
    
    @app_commands.command(name="fb-disconnect", description="Disconnect Facebook Page")






    async def disconnect(self, interaction: discord.Interaction):
        """Disconnect Facebook Page"""
        server_id = str(interaction.guild_id)
        
        account = db.get_facebook_account(server_id)
        if not account:
            await interaction.response.send_message(
                "❌ No Facebook Page connected.\n\nUse `/fb-connect` to connect a page.",
                ephemeral=True
            )
            return
        
        page_name = account.get('page_name', 'Facebook Page')
        db.delete_facebook_account(server_id)
        
        embed = discord.Embed(
            title="✅ Facebook Page Disconnected",
            description=f"Disconnected from **{page_name}**",
            color=config.COLOR_SUCCESS
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="fb-post", description="Post text or link to Facebook Page")
    @app_commands.describe(
        message="Text message for your post (required)",
        link="Optional: URL to share (website, video, etc.)"
    )







    async def post(self, interaction: discord.Interaction, message: str, link: str = None):
        """Post text/link to Facebook Page"""
        await interaction.response.defer()
        
        server_id = str(interaction.guild_id)
        account = db.get_facebook_account(server_id)
        
        if not account:
            await interaction.followup.send(
                "❌ No Facebook Page connected.\n\nUse `/fb-connect` first."
            )
            return
        
        try:
            # Rate limit check
            await self.rate_limiter.wait()
            
            # Post to Facebook
            post_id = await self.create_post(
                account['page_id'],
                account['access_token'],
                message,
                link
            )
            
            # Save to database
            db.save_facebook_post({
                'server_id': server_id,
                'page_id': account['page_id'],
                'fb_post_id': post_id,
                'message': message,
                'link': link,
                'status': 'published',
                'platform': 'facebook'
            })
            
            # Success message
            embed = discord.Embed(
                title="✅ Posted to Facebook!",
                description=message[:300] + ('...' if len(message) > 300 else ''),
                color=config.COLOR_SUCCESS
            )
            embed.add_field(name="📄 Page", value=account['page_name'], inline=True)
            embed.add_field(name="🆔 Post ID", value=post_id.split('_')[1][:10] + '...', inline=True)
            if link:
                embed.add_field(name="🔗 Link", value=link, inline=False)
            embed.set_footer(text=f"Posted at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Posting Failed",
                description=f"Error: {str(e)}",
                color=config.COLOR_ERROR
            )
            await interaction.followup.send(embed=error_embed)
    
    @app_commands.command(name="fb-post-image", description="Post image to Facebook Page")
    @app_commands.describe(
        image_url="Direct URL to the image (must be publicly accessible)",
        caption="Optional: Caption/message for the image"
    )




    async def post_image(self, interaction: discord.Interaction, image_url: str, caption: str = None):
        """Post image to Facebook Page"""
        await interaction.response.defer()
        
        server_id = str(interaction.guild_id)
        account = db.get_facebook_account(server_id)
        
        if not account:
            await interaction.followup.send("❌ No Facebook Page connected. Use `/fb-connect` first.")
            return
        
        try:
            await self.rate_limiter.wait()
            
            # Post image
            post_id = await self.post_photo(
                account['page_id'],
                account['access_token'],
                image_url,
                caption
            )
            
            # Save to database
            db.save_facebook_post({
                'server_id': server_id,
                'page_id': account['page_id'],
                'fb_post_id': post_id,
                'message': caption,
                'image_url': image_url,
                'status': 'published',
                'platform': 'facebook'
            })
            
            embed = discord.Embed(
                title="✅ Image Posted to Facebook!",
                description=caption[:200] if caption else "No caption",
                color=config.COLOR_SUCCESS
            )
            embed.set_thumbnail(url=image_url)
            embed.add_field(name="Page", value=account['page_name'])
            embed.add_field(name="Post ID", value=post_id.split('_')[1][:10] + '...')
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error posting image: {str(e)}")
    
    @app_commands.command(name="fb-schedule", description="Schedule a Facebook post for later")
    @app_commands.describe(
        message="Text message for your post",
        datetime_str="When to post (Format: YYYY-MM-DD HH:MM, e.g., 2025-11-05 14:30)",
        link="Optional: URL to share"
    )





    async def schedule(self, interaction: discord.Interaction, message: str, datetime_str: str, link: str = None):
        """Schedule a Facebook post"""
        server_id = str(interaction.guild_id)
        account = db.get_facebook_account(server_id)
        
        if not account:
            await interaction.response.send_message(
                "❌ No Facebook Page connected. Use `/fb-connect` first.",
                ephemeral=True
            )
            return
        
        try:
            # Parse datetime
            scheduled_at = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
            
            # Check if in future
            if scheduled_at <= datetime.utcnow():
                await interaction.response.send_message(
                    "❌ Schedule time must be in the future!\n\nExample: `2025-11-05 14:30`",
                    ephemeral=True
                )
                return
            
            # Save scheduled post
            post_id = db.save_facebook_post({
                'server_id': server_id,
                'page_id': account['page_id'],
                'message': message,
                'link': link,
                'scheduled_at': scheduled_at,
                'status': 'scheduled',
                'platform': 'facebook'
            })
            
            embed = discord.Embed(
                title="⏰ Facebook Post Scheduled!",
                description=f"Your post will be published on **{datetime_str} UTC**",
                color=config.COLOR_WARNING
            )
            embed.add_field(
                name="📝 Message Preview",
                value=message[:150] + ('...' if len(message) > 150 else ''),
                inline=False
            )
            if link:
                embed.add_field(name="🔗 Link", value=link, inline=False)
            embed.add_field(name="📄 Page", value=account['page_name'], inline=True)
            embed.set_footer(text=f"Scheduled ID: {str(post_id)[:10]}...")
            
            await interaction.response.send_message(embed=embed)
            
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid date format!\n\n**Correct format:** YYYY-MM-DD HH:MM\n**Example:** 2025-11-05 14:30",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Scheduling error: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="fb-recent", description="View recent posts from your Facebook Page")
    @app_commands.describe(count="Number of posts to show (max 100, default 10)")







    async def recent(self, interaction: discord.Interaction, count: int = 10):
        """Get recent posts from Facebook Page"""
        await interaction.response.defer()
        
        server_id = str(interaction.guild_id)
        account = db.get_facebook_account(server_id)
        
        if not account:
            await interaction.followup.send("❌ No Facebook Page connected. Use `/fb-connect` first.")
            return
        
        try:
            await self.rate_limiter.wait()
            
            url = f"{config.FACEBOOK_GRAPH_URL}/{account['page_id']}/feed"
            params = {
                'fields': 'id,message,created_time,permalink_url,shares,likes.summary(true),comments.summary(true)',
                'limit': min(count, 100),
                'access_token': account['access_token']
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        raise Exception(await resp.text())
                    
                    data = await resp.json()
                    posts = data.get('data', [])
                    
                    if not posts:
                        await interaction.followup.send("📭 No posts found on this page")
                        return
                    
                    embed = discord.Embed(
                        title=f"📘 Recent Facebook Posts",
                        description=f"From **{account['page_name']}** ({len(posts)} posts)",
                        color=config.COLOR_FACEBOOK
                    )
                    
                    for i, post in enumerate(posts[:5], 1):
                        message = post.get('message', 'No text')[:100]
                        likes = post.get('likes', {}).get('summary', {}).get('total_count', 0)
                        comments = post.get('comments', {}).get('summary', {}).get('total_count', 0)
                        shares = post.get('shares', {}).get('count', 0)
                        created = post.get('created_time', '')[:10]
                        
                        embed.add_field(
                            name=f"{i}. Post from {created}",
                            value=f"{message}{'...' if len(post.get('message', '')) > 100 else ''}\n\n👍 {likes} | 💬 {comments} | 🔄 {shares}\n[View Post]({post.get('permalink_url', '#')})",
                            inline=False
                        )
                    
                    if len(posts) > 5:
                        embed.set_footer(text=f"Showing 5 of {len(posts)} posts")
                    
                    await interaction.followup.send(embed=embed)
        
        except Exception as e:
            await interaction.followup.send(f"❌ Error fetching posts: {str(e)}")
    
    @app_commands.command(name="fb-stats", description="Get analytics for a Facebook post")
    @app_commands.describe(post_id="Facebook post ID (format: 123456789_987654321)")






    async def stats(self, interaction: discord.Interaction, post_id: str):
        """Get analytics for a Facebook post"""
        await interaction.response.defer()
        
        server_id = str(interaction.guild_id)
        account = db.get_facebook_account(server_id)
        
        if not account:
            await interaction.followup.send("❌ No Facebook Page connected. Use `/fb-connect` first.")
            return
        
        try:
            await self.rate_limiter.wait()
            
            # Get post insights
            url = f"{config.FACEBOOK_GRAPH_URL}/{post_id}/insights"
            params = {
                'metric': 'post_impressions,post_engaged_users,post_clicks,post_reactions_by_type_total',
                'access_token': account['access_token']
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        error = await resp.text()
                        raise Exception(f"API error: {error}")
                    
                    data = await resp.json()
                    insights = {}
                    
                    for item in data.get('data', []):
                        metric_name = item['name']
                        value = item['values'][0]['value']
                        insights[metric_name] = value
                    
                    # Save analytics
                    db.save_facebook_analytics({
                        'post_id': post_id,
                        'server_id': server_id,
                        **insights
                    })
                    
                    # Create analytics embed
                    embed = discord.Embed(
                        title="📊 Facebook Post Analytics",
                        description=f"Statistics for post: `{post_id}`",
                        color=config.COLOR_FACEBOOK
                    )
                    
                    embed.add_field(
                        name="👁️ Impressions",
                        value=f"{insights.get('post_impressions', 0):,}",
                        inline=True
                    )
                    embed.add_field(
                        name="👥 Engaged Users",
                        value=f"{insights.get('post_engaged_users', 0):,}",
                        inline=True
                    )
                    embed.add_field(
                        name="🖱️ Clicks",
                        value=f"{insights.get('post_clicks', 0):,}",
                        inline=True
                    )
                    
                    # Reactions breakdown
                    reactions = insights.get('post_reactions_by_type_total', {})
                    if reactions:
                        reaction_str = ' | '.join([f"{k}: {v}" for k, v in reactions.items()])
                        embed.add_field(
                            name="❤️ Reactions Breakdown",
                            value=reaction_str,
                            inline=False
                        )
                    
                    embed.set_footer(text=f"Data fetched at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
                    
                    await interaction.followup.send(embed=embed)
        
        except Exception as e:
            await interaction.followup.send(
                f"❌ Error fetching analytics: {str(e)}\n\nMake sure:\n• Post ID is correct (format: 123_456)\n• Post belongs to your connected page"
            )
    
    @app_commands.command(name="fb-delete", description="Delete a Facebook post")
    @app_commands.describe(post_id="Facebook post ID to delete")





    async def delete_post(self, interaction: discord.Interaction, post_id: str):
        """Delete a Facebook post"""
        await interaction.response.defer()
        
        server_id = str(interaction.guild_id)
        account = db.get_facebook_account(server_id)
        
        if not account:
            await interaction.followup.send("❌ No Facebook Page connected. Use `/fb-connect` first.")
            return
        
        try:
            await self.rate_limiter.wait()
            
            url = f"{config.FACEBOOK_GRAPH_URL}/{post_id}"
            params = {'access_token': account['access_token']}
            
            async with aiohttp.ClientSession() as session:
                async with session.delete(url, params=params) as resp:
                    if resp.status == 200:
                        embed = discord.Embed(
                            title="✅ Post Deleted",
                            description=f"Successfully deleted post: `{post_id}`",
                            color=config.COLOR_SUCCESS
                        )
                        await interaction.followup.send(embed=embed)
                    else:
                        error = await resp.text()
                        raise Exception(error)
        
        except Exception as e:
            await interaction.followup.send(f"❌ Error deleting post: {str(e)}")
    
    @app_commands.command(name="fb-page-info", description="Get information about your connected Facebook Page")




    async def page_info(self, interaction: discord.Interaction):
        """Get Facebook Page information"""
        await interaction.response.defer()
        
        server_id = str(interaction.guild_id)
        account = db.get_facebook_account(server_id)
        
        if not account:
            await interaction.followup.send("❌ No Facebook Page connected. Use `/fb-connect` first.")
            return
        
        try:
            await self.rate_limiter.wait()
            
            url = f"{config.FACEBOOK_GRAPH_URL}/{account['page_id']}"
            params = {
                'fields': 'id,name,fan_count,followers_count,category,about,website',
                'access_token': account['access_token']
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        raise Exception(await resp.text())
                    
                    page_data = await resp.json()
                    
                    embed = discord.Embed(
                        title=f"📘 {page_data.get('name', 'Facebook Page')}",
                        description=page_data.get('about', 'No description'),
                        color=config.COLOR_FACEBOOK,
                        url=page_data.get('website', f"https://facebook.com/{page_data['id']}")
                    )
                    
                    embed.add_field(
                        name="👥 Fans/Likes",
                        value=f"{page_data.get('fan_count', 0):,}",
                        inline=True
                    )
                    embed.add_field(
                        name="📊 Followers",
                        value=f"{page_data.get('followers_count', 0):,}",
                        inline=True
                    )
                    embed.add_field(
                        name="📂 Category",
                        value=page_data.get('category', 'Unknown'),
                        inline=True
                    )
                    embed.add_field(
                        name="🆔 Page ID",
                        value=page_data['id'],
                        inline=False
                    )
                    
                    await interaction.followup.send(embed=embed)
        
        except Exception as e:
            await interaction.followup.send(f"❌ Error fetching page info: {str(e)}")
    
    # Helper Methods




    async def create_post(self, page_id, access_token, message, link=None):
        """Create a text post on Facebook Page"""
        url = f"{config.FACEBOOK_GRAPH_URL}/{page_id}/feed"
        params = {
            'message': message,
            'access_token': access_token
        }
        
        if link:
            params['link'] = link
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data['id']
                else:
                    error = await resp.text()
                    raise Exception(f"Post failed: {error}")
    




    async def post_photo(self, page_id, access_token, image_url, caption=None):
        """Post photo to Facebook Page"""
        url = f"{config.FACEBOOK_GRAPH_URL}/{page_id}/photos"
        params = {
            'url': image_url,
            'access_token': access_token
        }
        
        if caption:
            params['caption'] = caption
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data['id']
                else:
                    error = await resp.text()
                    raise Exception(f"Image post failed: {error}")
    



    
    async def publish_scheduled_post(self, post):
        """Publish a scheduled Facebook post"""
        try:
            account = db.get_facebook_account(post['server_id'])
            if not account:
                db.update_facebook_post_status(post['_id'], 'failed')
                print(f"❌ No account found for server {post['server_id']}")
                return
            
            await self.rate_limiter.wait()
            
            # Post to Facebook
            post_id = await self.create_post(
                post['page_id'],
                account['access_token'],
                post['message'],
                post.get('link')
            )
            
            db.update_facebook_post_status(post['_id'], 'published', post_id)
            print(f'✅ Published scheduled Facebook post: {post_id}')
            
        except Exception as e:
            print(f'❌ Failed to publish scheduled post {post.get("_id")}: {e}')
            db.update_facebook_post_status(post['_id'], 'failed')


class RateLimiter:
    """Rate limiter for Facebook API"""
    def __init__(self):
        self.calls = []
        self.max_calls = config.FACEBOOK_MAX_CALLS
        self.window = config.RATE_LIMIT_WINDOW
    
    async def wait(self):
        """Wait if rate limit reached"""
        now = datetime.utcnow().timestamp()
        
        # Remove old calls outside the time window
        self.calls = [t for t in self.calls if t > now - self.window]
        
        # Check if limit reached
        if len(self.calls) >= self.max_calls:
            wait_time = self.calls[0] + self.window - now
            if wait_time > 0:
                print(f'⏸️  Facebook rate limit reached ({self.max_calls}/hour), waiting {wait_time:.0f}s')
                await asyncio.sleep(wait_time)
                self.calls = []
        
        self.calls.append(now)


async def setup(bot):
    """Load the cog"""
    await bot.add_cog(Facebook(bot))
