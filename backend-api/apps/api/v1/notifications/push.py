"""
G-Connect - Push notifications (architecture prête, envoi non activé)

Ce module isole le point d'intégration d'un fournisseur push (Firebase Cloud
Messaging, APNs...) du reste de l'application : `signals.py` appelle
`send_push_notification()` pour CHAQUE notification créée, mais l'implémentation
actuelle se contente de journaliser l'appel — aucun SDK, aucune credential,
aucun appel réseau externe. Brancher un fournisseur revient à réécrire
uniquement `_dispatch()` ci-dessous, sans toucher au reste du code.
"""
import logging

logger = logging.getLogger(__name__)


def send_push_notification(notification):
    """
    Point d'entrée unique pour l'envoi push. Reçoit l'instance `Notification`
    déjà enregistrée en base. Ne fait rien de plus qu'un log tant qu'aucun
    fournisseur n'est branché — voir `_dispatch()`.
    """
    from .models import NotificationPreference, DeviceToken

    if not NotificationPreference.for_user(notification.recipient).push_enabled:
        return

    tokens = list(DeviceToken.objects.filter(user=notification.recipient).values_list("token", flat=True))
    if not tokens:
        logger.debug("push: aucun device token pour %s, notification #%s non envoyée",
                     notification.recipient.username, notification.id)
        return

    title, body = _format(notification)
    _dispatch(tokens=tokens, title=title, body=body, notification=notification)


def _format(notification):
    actor_name = notification.actor.get_full_name() if notification.actor else "G-Connect"
    title = actor_name if notification.actor else "G-Connect"
    body = notification.verb
    return title, body


def _get_firebase_app():
    """Initialise l'app Firebase Admin une seule fois (singleton)."""
    import os
    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError:
        return None

    try:
        return firebase_admin.get_app()
    except ValueError:
        pass

    creds_path = os.environ.get('FIREBASE_CREDENTIALS_PATH')
    if not creds_path or not os.path.exists(creds_path):
        logger.warning("push: FIREBASE_CREDENTIALS_PATH non défini ou fichier introuvable — push désactivé.")
        return None

    cred = credentials.Certificate(creds_path)
    return firebase_admin.initialize_app(cred)


def _dispatch(tokens, title, body, notification):
    """Envoie via Firebase Cloud Messaging (multicast)."""
    app = _get_firebase_app()
    if app is None:
        logger.info(
            "push (non envoyé — firebase_admin non configuré) "
            "-> %s appareil(s) : [%s] %s (notification #%s, type=%s)",
            len(tokens), title, body, notification.id, notification.notification_type,
        )
        return

    try:
        from firebase_admin import messaging

        data_payload = {
            'notification_id': str(notification.id),
            'type': notification.notification_type,
        }
        if notification.target_id:
            data_payload['target_id'] = str(notification.target_id)
        if notification.target_type:
            data_payload['target_type'] = notification.target_type

        message = messaging.MulticastMessage(
            tokens=tokens,
            notification=messaging.Notification(title=title, body=body),
            data=data_payload,
            android=messaging.AndroidConfig(priority='high'),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound='default')
                )
            ),
        )
        response = messaging.send_each_for_multicast(message)
        logger.info(
            "push FCM: %s succès / %s échecs (notification #%s)",
            response.success_count, response.failure_count, notification.id,
        )

        # Nettoyer les tokens invalides
        if response.failure_count > 0:
            from .models import DeviceToken
            invalid = [
                tokens[i] for i, r in enumerate(response.responses)
                if not r.success and r.exception and 'registration-token-not-registered' in str(r.exception)
            ]
            if invalid:
                DeviceToken.objects.filter(token__in=invalid).delete()
                logger.info("push: %s tokens invalides supprimés", len(invalid))

    except Exception as exc:
        logger.error("push FCM erreur: %s (notification #%s)", exc, notification.id)
