"""
Signal post_save sur Message → broadcast WebSocket via Django Channels.
Tous les consommateurs connectés au groupe chat_<id> reçoivent le message,
sauf le canal de l'expéditeur (géré dans le consumer via sender_user_id).
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='messaging.Message')
def message_post_save(sender, instance, created, **kwargs):
    if not created or instance.is_deleted:
        return
    _broadcast_new_message(instance)


def _broadcast_new_message(message):
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        from .serializers import MessageSerializer

        channel_layer = get_channel_layer()
        if channel_layer is None:
            return

        data = MessageSerializer(message).data
        group_name = f'chat_{message.conversation_id}'
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'chat_message',
                'message': data,
                'sender_user_id': message.sender_id,
            },
        )
        logger.debug('WS broadcast: group=%s msg=%s', group_name, message.id)
    except Exception as exc:
        logger.error('WS broadcast error: %s', exc)
