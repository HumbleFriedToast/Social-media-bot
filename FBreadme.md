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
