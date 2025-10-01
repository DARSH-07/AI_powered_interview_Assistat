import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from .models import Candidate, InterviewSession, ChatMessage

logger = logging.getLogger(__name__)


class InterviewConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time interview updates"""
    
    async def connect(self):
        """Accept WebSocket connection"""
        await self.accept()
        logger.info(f"WebSocket connected: {self.channel_name}")
        
        # Send initial connection message
        await self.send(text_data=json.dumps({
            'type': 'connection',
            'message': 'Connected to interview assistant'
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnect"""
        logger.info(f"WebSocket disconnected: {self.channel_name}")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'message': 'Connection active'
                }))
                
            elif message_type == 'join_candidate':
                candidate_id = data.get('candidate_id')
                if candidate_id:
                    # Add to candidate group for updates
                    await self.channel_layer.group_add(
                        f'candidate_{candidate_id}',
                        self.channel_name
                    )
                    
            elif message_type == 'interview_update':
                # Broadcast interview updates to dashboard
                candidate_id = data.get('candidate_id')
                if candidate_id:
                    await self.channel_layer.group_send(
                        'dashboard_updates',
                        {
                            'type': 'interview_update_message',
                            'candidate_id': candidate_id,
                            'update_data': data.get('data', {})
                        }
                    )
                    
        except json.JSONDecodeError:
            logger.error("Invalid JSON received in WebSocket")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid message format'
            }))
        except Exception as e:
            logger.error(f"WebSocket receive error: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Message processing failed'
            }))
    
    async def interview_update_message(self, event):
        """Send interview update to connected clients"""
        await self.send(text_data=json.dumps({
            'type': 'interview_update',
            'candidate_id': event['candidate_id'],
            'data': event['update_data']
        }))


class DashboardConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for dashboard real-time updates"""
    
    async def connect(self):
        """Accept WebSocket connection and join dashboard group"""
        await self.accept()
        await self.channel_layer.group_add('dashboard_updates', self.channel_name)
        logger.info(f"Dashboard WebSocket connected: {self.channel_name}")
        
        await self.send(text_data=json.dumps({
            'type': 'connection',
            'message': 'Connected to dashboard updates'
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnect"""
        await self.channel_layer.group_discard('dashboard_updates', self.channel_name)
        logger.info(f"Dashboard WebSocket disconnected: {self.channel_name}")
    
    async def receive(self, text_data):
        """Handle incoming dashboard messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'message': 'Dashboard connection active'
                }))
                
        except Exception as e:
            logger.error(f"Dashboard WebSocket receive error: {str(e)}")
    
    async def interview_update_message(self, event):
        """Forward interview updates to dashboard"""
        await self.send(text_data=json.dumps({
            'type': 'interview_update',
            'candidate_id': event['candidate_id'],
            'data': event['update_data']
        }))