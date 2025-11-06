"""
OAuth handler for Facebook Pages
Manages Facebook authentication and token exchange
"""

import aiohttp
from urllib.parse import urlencode
from aiohttp import web
import asyncio
import config


class FacebookOAuth:
    """OAuth handler for Facebook Pages"""
    
    def __init__(self):
        self.app_id = config.FACEBOOK_APP_ID
        self.app_secret = config.FACEBOOK_APP_SECRET
        self.redirect_uri = config.REDIRECT_URI
        self.pending_auth = {}  # server_id -> Future
        self.server = None
        self.runner = None
    
    def get_auth_url(self, server_id):
        """Generate Facebook OAuth URL"""
        params = {
            'client_id': self.app_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'pages_show_list,pages_read_engagement,pages_manage_posts,pages_read_user_content,read_insights',
            'response_type': 'code',
            'state': str(server_id)
        }
        return f"{config.FACEBOOK_OAUTH_URL}?{urlencode(params)}"
    
    async def exchange_code(self, code):
        """Exchange authorization code for user access token"""
        params = {
            'client_id': self.app_id,
            'client_secret': self.app_secret,
            'redirect_uri': self.redirect_uri,
            'code': code
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(config.FACEBOOK_TOKEN_URL, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('access_token')
                else:
                    error = await resp.text()
                    raise Exception(f"Token exchange failed: {error}")
    
    async def get_long_lived_token(self, short_token):
        """Get long-lived user token (60 days)"""
        params = {
            'grant_type': 'fb_exchange_token',
            'client_id': self.app_id,
            'client_secret': self.app_secret,
            'fb_exchange_token': short_token
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(config.FACEBOOK_TOKEN_URL, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('access_token')
                return short_token  # Return original if exchange fails
    
    async def get_user_pages(self, user_token):
        """Get list of pages user manages"""
        url = f"{config.FACEBOOK_GRAPH_URL}/me/accounts"
        params = {
            'access_token': user_token,
            'fields': 'id,name,access_token,tasks'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    error = await resp.text()
                    raise Exception(f"Failed to get pages: {error}")
    
    async def handle_callback(self, request):
        """Handle OAuth callback from Facebook"""
        code = request.query.get('code')
        server_id = request.query.get('state')
        error = request.query.get('error')
        
        if error:
            error_desc = request.query.get('error_description', 'Unknown error')
            return web.Response(text=f'❌ Authorization failed: {error_desc}')
        
        if code and server_id:
            try:
                # Exchange code for user token
                user_token = await self.exchange_code(code)
                
                # Get long-lived user token
                long_token = await self.get_long_lived_token(user_token)
                
                # Get user's pages
                pages_data = await self.get_user_pages(long_token)
                
                # Notify waiting command with pages
                if server_id in self.pending_auth:
                    self.pending_auth[server_id].set_result(pages_data)
                
                return web.Response(text='✅ Facebook connected! You can close this window and return to Discord.')
            except Exception as e:
                print(f'❌ OAuth error: {e}')
                if server_id in self.pending_auth:
                    self.pending_auth[server_id].set_exception(e)
                return web.Response(text=f'❌ Error: {str(e)}')
        
        return web.Response(text='❌ Invalid callback - missing code or state')
    
    async def start_server(self):
        """Start OAuth callback server"""
        if self.server:
            return  # Already running
        
        try:
            app = web.Application()
            app.router.add_get('/callback', self.handle_callback)
            
            self.runner = web.AppRunner(app)
            await self.runner.setup()
            site = web.TCPSite(self.runner, 'localhost', config.OAUTH_PORT)
            await site.start()
            print(f'✅ OAuth callback server started: http://localhost:{config.OAUTH_PORT}')
            self.server = site
        except Exception as e:
            print(f'❌ Failed to start OAuth server: {e}')
            raise
    
    async def stop_server(self):
        """Stop OAuth callback server"""
        if self.runner:
            await self.runner.cleanup()
            self.server = None
            self.runner = None
            print('✅ OAuth server stopped')


# Global OAuth handler
oauth = FacebookOAuth()
