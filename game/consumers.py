import json
from channels.generic.websocket import AsyncWebsocketConsumer


class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.join_code = self.scope["url_route"]["kwargs"]["join_code"]
        self.group_name = f"game_{self.join_code}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # Clients only receive; moves are made via the REST API
    async def receive(self, text_data=None, bytes_data=None):
        pass

    async def game_update(self, event):
        await self.send(text_data=json.dumps(event["data"]))
