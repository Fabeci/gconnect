# messaging/pagination.py
from rest_framework.pagination import PageNumberPagination


class ConversationPagination(PageNumberPagination):
    """Le frontend ne paginait pas encore les conversations (pas de
    'charger plus') — page_size généreux pour ne pas tronquer la liste
    d'un utilisateur actif tout en bornant la requête dans le pire cas."""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


class MessagePagination(PageNumberPagination):
    """Idem pour l'historique de messages : le frontend affiche
    aujourd'hui tout l'historique reçu sans 'charger plus'. Un page_size
    large couvre l'immense majorité des conversations réelles tout en
    bornant la requête pour les cas pathologiques (des dizaines de
    milliers de messages)."""
    page_size = 200
    page_size_query_param = 'page_size'
    max_page_size = 500
