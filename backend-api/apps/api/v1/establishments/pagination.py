"""
G-Connect - Establishments Pagination
"""

from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """Pagination standard : 20 établissements par page"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class GenerousResultsSetPagination(PageNumberPagination):
    """Pour les endpoints qui n'avaient aucune pagination et dont le
    frontend ne gère pas encore de 'charger plus' (commentaires, réactions,
    promotions, candidatures...). Une taille de page large borne les
    requêtes dans le pire cas (post viral, etc.) sans tronquer visiblement
    les listes réelles, qui dépassent rarement quelques dizaines d'éléments."""
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 300
