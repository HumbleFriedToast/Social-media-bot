# instagram_cog.py
from discord import app_commands, ui
from discord.ext import commands
import discord
import requests
import sqlite3
import os
from urllib.parse import urlencode
import asyncio

DB_PATH = 'database.db'

APP_ID = os.getenv("APP_ID")
APP_SECRET = os.getenv("APP_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
GRAPH_API_VERSION = "v20.0"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_id TEXT NOT NULL UNIQUE,
            username TEXT NOT NULL,
            instagram_token TEXT NOT NULL,
            instagram_id TEXT
        );
    ''')
    conn.close()


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def insert_user(discord_id, username, token, instagram_id=None):
    conn = get_db_connection()
    with conn:
        conn.execute('''
            INSERT OR REPLACE INTO users (discord_id, username, instagram_token, instagram_id)
            VALUES (?, ?, ?, ?)
        ''', (discord_id, username, token, instagram_id))
    conn.close()


def remove_user(discord_id):
    conn = get_db_connection()
    with conn:
        conn.execute('DELETE FROM users WHERE discord_id = ?', (discord_id,))
    conn.close()


def get_user_data(discord_id):
    conn = get_db_connection()
    cursor = conn.execute('SELECT * FROM users WHERE discord_id = ?', (str(discord_id),))
    row = cursor.fetchone()
    conn.close()
    return row


def call_api(params, endpoint):
    resp = requests.get(f"https://graph.instagram.com/{endpoint}", params=params)
    return resp.json()


def call_api_post(params, endpoint):
    resp = requests.post(f"https://graph.instagram.com/{endpoint}", data=params)
    try:
        return resp.json()
    except ValueError:
        return {"error": "invalid_json_response", "status_code": resp.status_code, "text": resp.text}


def format_dict(data, indent=0):
    if not isinstance(data, dict):
        return str(data)
    formatted = ""
    for key, value in data.items():
        if isinstance(value, dict):
            formatted += f"{' ' * indent}**{key}**:\n{format_dict(value, indent + 2)}\n"
        elif isinstance(value, list):
            formatted += f"{' ' * indent}**{key}**:\n"
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    formatted += f"{' ' * (indent + 2)}[{i + 1}] {format_dict(item, indent + 4)}\n"
                else:
                    formatted += f"{' ' * (indent + 2)}[{i + 1}] `{item}`\n"
        else:
            formatted += f"{' ' * indent}**{key}**: `{value}`\n"
    return formatted


def shorten_url(url, max_len=40):
    if len(url) <= max_len:
        return url
    return url[:max_len] + "..."


class InstagramPostsView(ui.View):
    def __init__(self, post_data, token):
        super().__init__(timeout=None)
        self.post_data = post_data
        self.token = token

    @ui.button(label="Delete Post", style=discord.ButtonStyle.danger)
    async def delete_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        resp = requests.delete(f"https://graph.instagram.com/{self.post_data['id']}", params={"access_token": self.token})
        result = resp.json() if resp.text else {"status": "success"}
        await interaction.followup.send(f"Post deleted:\n{format_dict(result)}", ephemeral=True)
        self.stop()

    @ui.button(label="View Details", style=discord.ButtonStyle.secondary)
    async def details_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(f"Post Details:\n{format_dict(self.post_data)}", ephemeral=True)

    @ui.button(label="View Insights", style=discord.ButtonStyle.primary)
    async def view_insights(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        post_type = self.post_data.get("media_type", "IMAGE").lower()

        metrics_map = {
            "image": "reach,likes,comments,saved",
            "video": "reach,likes,comments,video_views,shares",
            "reels": "reach,likes,comments,plays,shares,saved"
        }

        metrics = metrics_map.get(post_type, "reach,likes,comments")
        params = {"metric": metrics, "access_token": self.token}
        resp = call_api(params, f"{self.post_data['id']}/insights")

        embed = discord.Embed(title=f"Insights for Post {self.post_data['id']}", color=discord.Color.green())
        if "data" in resp and isinstance(resp["data"], list):
            for metric in resp["data"]:
                name = metric.get("name", "Unknown")
                values = metric.get("values", [])
                if values:
                    embed.add_field(name=name, value=str(values[-1].get("value", "N/A")), inline=True)
        else:
            embed.description = str(resp)
        await interaction.followup.send(embed=embed, ephemeral=True)


class InstagramCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        init_db()

    async def get_token_or_error(self, interaction):
        user = get_user_data(interaction.user.id)
        if not user:
            await interaction.response.send_message("You are not registered. Use /insta_login_dev first.", ephemeral=True)
            return None, None
        token = user["instagram_token"]
        ig_id = user["instagram_id"] or user["username"]
        return token, ig_id

    @app_commands.command(name="insta_login_dev", description="Manually register a token")
    @app_commands.describe(token="Your Instagram access token", username="Your Instagram username", instagram_id="Instagram numeric ID (optional)")
    async def insta_login_dev(self, interaction: discord.Interaction, token: str, username: str, instagram_id: str = None):
        await interaction.response.defer(ephemeral=True)
        insert_user(str(interaction.user.id), username, token, instagram_id)
        await interaction.followup.send("Token manually inserted into database.", ephemeral=True)

    @app_commands.command(name="instagram_post", description="Post an image with caption")
    @app_commands.describe(caption="Text caption for the image", image_url="URL of the image to post")
    async def instagram_post(self, interaction: discord.Interaction, caption: str, image_url: str):
        await interaction.response.defer(ephemeral=True)
        token, ig_id = await self.get_token_or_error(interaction)
        if not token:
            return

        params_create = {"image_url": image_url, "caption": caption, "access_token": token}
        create_resp = call_api_post(params_create, f"{ig_id}/media")
        if "id" not in create_resp:
            await interaction.followup.send(f"Failed to create post: {create_resp}", ephemeral=True)
            return
        creation_id = create_resp["id"]

        # Wait until media is ready
        for _ in range(10):
            status = call_api({"fields": "status_code", "access_token": token}, creation_id)
            if status.get("status_code") == "FINISHED":
                break
            await asyncio.sleep(2)

        publish_resp = call_api_post({"creation_id": creation_id, "access_token": token}, f"{ig_id}/media_publish")
        await interaction.followup.send(f"Post published:\n```json\n{publish_resp}\n```", ephemeral=True)

    @app_commands.command(name="instagram_post_reel", description="Post a reel with caption")
    @app_commands.describe(caption="Text caption for the reel", video_url="URL of the video to post")
    async def instagram_post_reel(self, interaction: discord.Interaction, caption: str, video_url: str):
        await interaction.response.defer(ephemeral=True)
        token, ig_id = await self.get_token_or_error(interaction)
        if not token:
            return

        params_create = {"media_type": "REELS", "video_url": video_url, "caption": caption, "access_token": token}
        create_resp = call_api_post(params_create, f"{ig_id}/media")
        if "id" not in create_resp:
            await interaction.followup.send(f"Failed to create reel: {create_resp}", ephemeral=True)
            return
        creation_id = create_resp["id"]

        for _ in range(10):
            status = call_api({"fields": "status_code", "access_token": token}, creation_id)
            if status.get("status_code") == "FINISHED":
                break
            await asyncio.sleep(2)

        publish_resp = call_api_post({"creation_id": creation_id, "access_token": token}, f"{ig_id}/media_publish")
        await interaction.followup.send(f"Reel published:\n```json\n{publish_resp}\n```", ephemeral=True)

    @app_commands.command(name="instagram_posts", description="Get all your Instagram posts")
    async def get_all_posts(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        token, _ = await self.get_token_or_error(interaction)
        if not token:
            return

        params = {"fields": "id,caption,media_type,media_url,permalink,timestamp", "access_token": token}
        result = call_api(params, "me/media")
        if "data" not in result or not result["data"]:
            await interaction.followup.send("No posts found.", ephemeral=True)
            return

        for post in result["data"]:
            caption = post.get('caption', 'No caption')
            media_type = post.get('media_type')
            media_url = post.get('media_url', '')
            url_short = shorten_url(media_url)
            timestamp = post.get('timestamp', '')

            embed = discord.Embed(title=f"Post {post['id']}", color=discord.Color.blue())
            embed.add_field(name="Caption", value=caption, inline=False)
            embed.add_field(name="Type", value=media_type, inline=True)
            embed.add_field(name="URL", value=url_short, inline=False)
            embed.add_field(name="Timestamp", value=timestamp, inline=True)
            if media_url:
                embed.set_image(url=media_url)

            view = InstagramPostsView(post, token)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="disconnect", description="Disconnect your Instagram account from the bot")
    async def disconnect(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        remove_user(str(interaction.user.id))
        await interaction.followup.send("Your Instagram account has been disconnected.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(InstagramCog(bot))
