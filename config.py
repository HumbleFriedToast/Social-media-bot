"""
Configuration file for Facebook Discord Bot
Loads environment variables and provides settings
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Discord Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Facebook Configuration
FACEBOOK_APP_ID = os.getenv('FACEBOOK_APP_ID')
FACEBOOK_APP_SECRET = os.getenv('FACEBOOK_APP_SECRET')
FACEBOOK_MAX_CALLS = int(os.getenv('FACEBOOK_MAX_CALLS', 180))
FACEBOOK_API_VERSION = 'v21.0'

# OAuth Configuration
REDIRECT_URI = os.getenv('REDIRECT_URI', 'http://localhost:8080/callback')
OAUTH_PORT = 8080

# Database Configuration
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'social_media_bot')

# Security Configuration
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')

# Rate Limiting
RATE_LIMIT_WINDOW = 3600  # 1 hour in seconds

# Scheduler Configuration
SCHEDULER_CHECK_INTERVAL = 60  # Check every 60 seconds

# Facebook API URLs
FACEBOOK_OAUTH_URL = 'https://www.facebook.com/v21.0/dialog/oauth'
FACEBOOK_TOKEN_URL = f'https://graph.facebook.com/{FACEBOOK_API_VERSION}/oauth/access_token'
FACEBOOK_GRAPH_URL = f'https://graph.facebook.com/{FACEBOOK_API_VERSION}'

# Discord Embed Colors
COLOR_FACEBOOK = 0x1877F2  # Facebook blue
COLOR_SUCCESS = 0x00FF00   # Green
COLOR_ERROR = 0xFF0000     # Red
COLOR_WARNING = 0xFFA500   # Orange

def validate_config():
    """Validate required environment variables"""
    if not DISCORD_TOKEN:
        raise ValueError("DISCORD_TOKEN not set in .env file")
    
    if not FACEBOOK_APP_ID or not FACEBOOK_APP_SECRET:
        raise ValueError("FACEBOOK_APP_ID and FACEBOOK_APP_SECRET must be set in .env")
    
    if not ENCRYPTION_KEY:
        from cryptography.fernet import Fernet
        key = Fernet.generate_key().decode()
        print("\n" + "="*60)
        print(" ENCRYPTION_KEY not found in .env!")
        print("Add this line to your .env file:")
        print(f"ENCRYPTION_KEY={key}")
        print("="*60 + "\n")
        raise ValueError("ENCRYPTION_KEY not set")

# Validate on import
validate_config()
