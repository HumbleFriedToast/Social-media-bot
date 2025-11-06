
# MINI PROJECT 14: Social Media Tracker
This project aims to create a bot that allows the user to connect to different Social Media platforms at Once. and be able to view and post from a simple
discord Command.
## Main Components 
Instagram Cog
Facebook Cog
Linkdin Cog

# Instagram Discord Bot Cog

This cog allows users to connect their Instagram accounts via OAuth or manually, view posts, delete posts, and view insights. Users are tracked in a SQLite database by Discord ID.

## Setup

1. Install dependencies:

```
pip install discord.py requests python-dotenv
```

2. Create a `.env` file with:

```
APP_ID=your_facebook_app_id
APP_SECRET=your_facebook_app_secret
REDIRECT_URI=https://yourredirect.uri/callback
```

3. Ensure `database.db` exists or will be created automatically.

4. Load the cog in your bot:

```python
await bot.load_extension("cogs.instagram_cog")
```

## Commands

### `/instagram_login`

* Starts the OAuth flow to connect Instagram account.
* Stores token and username in database.

### `/insta_login_dev token username`

* Manually register a token for testing or dev purposes.
* Stores token and username in database.

### `/instagram_posts`

* Lists all Instagram posts for the connected account.
* Displays embedded image, caption, type, timestamp, and shortened URL.
* Adds buttons per post:

  * **Delete Post**: Deletes the post.
  * **View Details**: Shows all data for the post.
  * **View Insights**: Shows metrics depending on media type:

    * IMAGE: `reach, likes, comments, saved`
    * VIDEO: `reach, likes, comments, video_views, shares`
    * REELS: `reach, likes, comments, plays, shares, saved`
### `/Instagram_Post`
  * ***Content***: The title of the content you are about to post
  * ***Media_Url***: a url to a standard image format file

### `/Instagram_Post_reel`
  * ***Content***: The title of the content you are about to post
  * ***Media_Url***: a url to a standard VIDEO format file(with the right codec and proper image resolution)

### `/disconnect`

* Removes the user from the database.
* Disconnects Instagram account from bot.

## Database

* `users` table:

  * `discord_id`: Discord user ID (unique)
  * `username`: Instagram username
  * `instagram_token`: Access token for API calls

# Dev:
***NOTES***: for some reason the Facebook account Oauth method gives an error with the accounts i tried to connect to. but the connection method should be correct so please bare in mind that
alternatively you can use your own APP_ID and APP_SECRET to and get a token for a developer account using the "insta_login_dev"



## FaceBook Discord Bot Cog
# Dev:
***NOTES***:Requires MongoDB to be setup. with these parameters: 
"MONGODB_URI=mongodb://localhost:27017/
DATABASE_NAME=social_media_bot"
### Module Structure

**`main.py`** - Bot entry point
- Initializes Discord bot
- Loads Facebook cog
- Syncs slash commands
- Handles bot lifecycle

**`config.py`** - Configuration management
- Loads environment variables
- Validates required settings
- Provides constants 

**`cogs/facebook.py`** - Facebook commands
- All slash command implementations
- Facebook API integration
- Rate limiting
- Error handling

**`utils/database.py`** - Database operations
- MongoDB connection
- CRUD operations for accounts/posts/analytics
- Token encryption/decryption

**`utils/oauth.py`** - OAuth authentication
- OAuth URL generation
- Token exchange
- Long-lived token conversion
- Callback server

**`utils/scheduler.py`** - Post scheduling
- APScheduler integration
- Periodic checks for scheduled posts
- Automatic publishing
