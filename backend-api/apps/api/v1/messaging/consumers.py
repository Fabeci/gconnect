"""
G-Connect — ChatConsumer WebSocket.

URL : ws://<host>/ws/chat/<conversation_id>/?token=<auth_token>

Architecture :
  • Flutter envoie les messages via HTTP (chemin existant + offline queue).
  • Le signal post_save de Message diffuse au groupe channel via send_message_to_group().
  • Le consumer WebSocket reçoit le broadcast et le transmet aux clients connectés,
    en excluant le canal de l'expéditeur (déjà mis à jour via HTTP).
  • Le consumer gère aussi l'indicateur de frappe (typing) et les accusés de lecture.

Messages entrants (client → serveur) :
  {"type": "typing", "is_typing": true}
  {"type": "read"}

Messages sortants (serveur → client) :
  {"type": "message",   "message": {<MessageSerializer>}}
  {"type": "typing",    "user_id": 42, "is_typing": true}
  {"type": "read",      "user_id": 42}
  {"type": "error",     "message": "..."}
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):

    # ── Connexion ─────────────────────────────────────────────────────────────

    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.group_name = f'chat_{self.conversation_id}'
        self.user = self.scope.get('user')

        if not self.user or isinstance(self.user, AnonymousUser):
            await self.close(code=4001)
            return

        if not await self._check_participant():
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self._set_online(True)
        logger.debug('WS connect: user=%s conv=%s', self.user.id, self.conversation_id)

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        if hasattr(self, 'user') and not isinstance(self.user, AnonymousUser):
            await self._set_online(False)

    # ── Réception depuis le client ────────────────────────────────────────────

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except (json.JSONDecodeError, ValueError):
            await self._send_error('Format JSON invalide.')
            return

        msg_type = data.get('type')

        if msg_type == 'typing':
            is_typing = bool(data.get('is_typing', True))
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'chat_typing',
                    'user_id': self.user.id,
                    'is_typing': is_typing,
                    'origin_channel': self.channel_name,
                },
            )

        elif msg_type == 'read':
            await self._mark_read()
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'chat_read',
                    'user_id': self.user.id,
                    'origin_channel': self.channel_name,
                },
            )

    # ── Handlers de groupe (group_send → send) ───────────────────────────────

    async def chat_message(self, event):
        """Déclenché par send_message_to_group() depuis le signal post_save."""
        if event.get('sender_user_id') == self.user.id:
            return  # ne pas renvoyer le message à son propre expéditeur
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
        }))

    async def chat_typing(self, event):
        if event.get('origin_channel') != self.channel_name:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user_id': event['user_id'],
                'is_typing': event['is_typing'],
            }))

    async def chat_read(self, event):
        if event.get('origin_channel') != self.channel_name:
            await self.send(text_data=json.dumps({
                'type': 'read',
                'user_id': event['user_id'],
            }))

    # ── Helpers DB ────────────────────────────────────────────────────────────

    @database_sync_to_async
    def _check_participant(self):
        from .models import ConversationParticipant
        return ConversationParticipant.objects.filter(
            conversation_id=self.conversation_id,
            user=self.user,
            is_active=True,
        ).exists()

    @database_sync_to_async
    def _mark_read(self):
        from .models import ConversationParticipant
        from django.utils import timezone
        ConversationParticipant.objects.filter(
            conversation_id=self.conversation_id,
            user=self.user,
        ).update(last_read_at=timezone.now(), unread_count=0)

    @database_sync_to_async
    def _set_online(self, online: bool):
        from .models import ConversationParticipant
        from django.utils import timezone
        update = {'is_online': online}
        if not online:
            update['last_seen'] = timezone.now()
        ConversationParticipant.objects.filter(
            conversation_id=self.conversation_id,
            user=self.user,
        ).update(**update)

    async def _send_error(self, message: str):
        await self.send(text_data=json.dumps({'type': 'error', 'message': message}))
