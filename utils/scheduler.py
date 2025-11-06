"""
Post scheduler for scheduled Facebook posts
Uses APScheduler to check and publish scheduled posts
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import asyncio


class PostScheduler:
    """Scheduler for Facebook posts"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.facebook_callback = None
        self.is_running = False
    
    def start(self):
        """Start the scheduler"""
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
            print('✅ Post scheduler started')
    
    def stop(self):
        """Stop the scheduler"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            print('✅ Post scheduler stopped')
    
    def set_facebook_callback(self, callback):
        """Set the function to call when publishing Facebook posts"""
        self.facebook_callback = callback
        print('✅ Facebook callback registered')
    
    async def check_scheduled_posts(self, db):
        """Check for Facebook posts that need to be published"""
        if not self.facebook_callback:
            return
        
        try:
            posts = db.get_facebook_scheduled_posts()
            
            if posts:
                print(f'📅 Found {len(posts)} scheduled posts to publish')
            
            for post in posts:
                try:
                    await self.facebook_callback(post)
                except Exception as e:
                    print(f'❌ Error publishing scheduled post {post.get("_id")}: {e}')
        except Exception as e:
            print(f'❌ Error checking scheduled posts: {e}')
    
    def schedule_check(self, db):
        """Schedule periodic checks for posts"""
        if not self.scheduler.get_job('check_facebook_posts'):
            self.scheduler.add_job(
                self.check_scheduled_posts,
                'interval',
                minutes=1,
                args=[db],
                id='check_facebook_posts',
                name='Check Facebook Scheduled Posts'
            )
            print('✅ Scheduled post checker configured (runs every 1 minute)')


# Global scheduler
scheduler = PostScheduler()
