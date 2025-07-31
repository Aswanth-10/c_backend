import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import Notification


class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time notifications"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.user = self.scope["user"]
        
        if isinstance(self.user, AnonymousUser):
            await self.close()
            return
        
        # Join user-specific group
        self.group_name = f"user_{self.user.id}"
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial unread notification count
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'notification_count',
            'unread_count': unread_count
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'mark_as_read':
                notification_id = data.get('notification_id')
                await self.mark_notification_as_read(notification_id)
            
            elif message_type == 'mark_all_as_read':
                await self.mark_all_notifications_as_read()
        
        except json.JSONDecodeError:
            pass
    
    async def notification_message(self, event):
        """Send notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification_type': event['notification_type'],
            'title': event['title'],
            'message': event['message'],
            'data': event.get('data', {})
        }))
        
        # Update unread count
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'notification_count',
            'unread_count': unread_count
        }))
    
    async def analytics_update(self, event):
        """Send analytics update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'analytics_update',
            'form_id': event['form_id'],
            'data': event['data']
        }))
    
    async def new_response(self, event):
        """Send new response notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'new_response',
            'form_id': event['form_id'],
            'response_id': event['response_id'],
            'form_title': event['form_title']
        }))
    
    @database_sync_to_async
    def get_unread_count(self):
        """Get count of unread notifications"""
        return Notification.objects.filter(
            user=self.user, 
            is_read=False
        ).count()
    
    @database_sync_to_async
    def mark_notification_as_read(self, notification_id):
        """Mark a specific notification as read"""
        try:
            notification = Notification.objects.get(
                id=notification_id, 
                user=self.user
            )
            notification.is_read = True
            notification.save()
        except Notification.DoesNotExist:
            pass
    
    @database_sync_to_async
    def mark_all_notifications_as_read(self):
        """Mark all notifications as read"""
        Notification.objects.filter(
            user=self.user, 
            is_read=False
        ).update(is_read=True)


class FormAnalyticsConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time form analytics"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.user = self.scope["user"]
        
        if isinstance(self.user, AnonymousUser):
            await self.close()
            return
        
        # Join form analytics group
        self.group_name = f"form_analytics_{self.user.id}"
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
    
    async def analytics_update(self, event):
        """Send analytics update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'analytics_update',
            'form_id': event['form_id'],
            'analytics': event['analytics']
        }))


# Utility function to send notifications to groups
def send_notification_to_group(group_name, notification_type, title, message, data=None):
    """Send notification to a specific group"""
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'notification_message',
            'notification_type': notification_type,
            'title': title,
            'message': message,
            'data': data or {}
        }
    )


def send_analytics_update(group_name, form_id, analytics_data):
    """Send analytics update to a specific group"""
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    'type': 'analytics_update',
                    'form_id': form_id,
                    'analytics': analytics_data
                }
            )
    except Exception as e:
        print(f"Failed to send analytics update: {str(e)}")


def send_new_response_notification(group_name, form_id, response_id, form_title):
    """Send new response notification to a specific group"""
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    'type': 'new_response',
                    'form_id': form_id,
                    'response_id': response_id,
                    'form_title': form_title
                }
            )
    except Exception as e:
        print(f"Failed to send new response notification: {str(e)}") 