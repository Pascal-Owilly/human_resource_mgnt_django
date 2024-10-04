from channels.generic.websocket import AsyncWebsocketConsumer
import json

class FileUploadConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.request_id = self.scope['url_route']['kwargs']['request_id']
        await self.channel_layer.group_add(
            self.request_id,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.request_id,
            self.channel_name
        )

    async def send_message(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': message
        }))

    async def send_progress(self, event):
        progress = event['progress']
        await self.send(text_data=json.dumps({
            'type': 'progress',
            'progress': progress
        }))
