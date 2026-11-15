"""
G-Connect - Posts URLs
Configuration des URLs pour l'application des publications
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PostViewSet, OpportunityViewSet, EventViewSet, ProjectViewSet,
    ApplicationViewSet, RSVPViewSet, CommentViewSet, ReactionViewSet,
    BookmarkViewSet
)

# Créer le router
router = DefaultRouter()
router.register(r'posts', PostViewSet, basename='post')
router.register(r'opportunities', OpportunityViewSet, basename='opportunity')
router.register(r'events', EventViewSet, basename='event')
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'applications', ApplicationViewSet, basename='application')
router.register(r'rsvps', RSVPViewSet, basename='rsvp')
router.register(r'comments', CommentViewSet, basename='comment')
router.register(r'reactions', ReactionViewSet, basename='reaction')
router.register(r'bookmarks', BookmarkViewSet, basename='bookmark')

app_name = 'posts'

urlpatterns = [
    path('', include(router.urls)),
]

"""
URLs disponibles:

POSTS (Publications):
- GET    /posts/                                  → Liste des publications (feed)
- POST   /posts/                                  → Créer une publication
- GET    /posts/{id}/                             → Détails d'une publication
- PUT    /posts/{id}/                             → Modifier
- PATCH  /posts/{id}/                             → Modifier partiellement
- DELETE /posts/{id}/                             → Supprimer

- POST   /posts/{id}/react/                       → Réagir
- POST   /posts/{id}/unreact/                     → Retirer réaction
- POST   /posts/{id}/share/                       → Partager
- POST   /posts/{id}/bookmark/                    → Sauvegarder
- POST   /posts/{id}/unbookmark/                  → Retirer sauvegarde
- POST   /posts/{id}/pin/                         → Épingler
- POST   /posts/{id}/unpin/                       → Désépingler
- POST   /posts/{id}/archive/                     → Archiver
- POST   /posts/{id}/increment_views/             → Incrémenter vues

- GET    /posts/feed/                             → Feed personnalisé
- GET    /posts/my_posts/                         → Mes publications
- GET    /posts/bookmarked/                       → Publications sauvegardées
- GET    /posts/trending/                         → Tendances

OPPORTUNITIES (Opportunités):
- GET    /opportunities/                          → Liste des opportunités
- POST   /opportunities/                          → Créer une opportunité
- GET    /opportunities/{id}/                     → Détails
- PUT    /opportunities/{id}/                     → Modifier
- PATCH  /opportunities/{id}/                     → Modifier partiellement
- DELETE /opportunities/{id}/                     → Supprimer

- POST   /opportunities/{id}/apply/               → Postuler
- POST   /opportunities/{id}/close/               → Fermer
- POST   /opportunities/{id}/reopen/              → Rouvrir
- GET    /opportunities/{id}/applications/        → Liste des candidatures
- GET    /opportunities/recommended/              → Recommandations

EVENTS (Événements):
- GET    /events/                                 → Liste des événements
- POST   /events/                                 → Créer un événement
- GET    /events/{id}/                            → Détails
- PUT    /events/{id}/                            → Modifier
- PATCH  /events/{id}/                            → Modifier partiellement
- DELETE /events/{id}/                            → Supprimer

- POST   /events/{id}/rsvp/                       → Répondre (RSVP)
- GET    /events/{id}/attendees/                  → Liste des participants
- GET    /events/upcoming/                        → Événements à venir
- GET    /events/my_events/                       → Mes événements

PROJECTS (Projets):
- GET    /projects/                               → Liste des projets
- POST   /projects/                               → Créer un projet
- GET    /projects/{id}/                          → Détails
- PUT    /projects/{id}/                          → Modifier
- PATCH  /projects/{id}/                          → Modifier partiellement
- DELETE /projects/{id}/                          → Supprimer

- POST   /projects/{id}/join/                     → Rejoindre l'équipe
- POST   /projects/{id}/leave/                    → Quitter l'équipe
- GET    /projects/looking_for_members/           → Projets recrutant

APPLICATIONS (Candidatures):
- GET    /applications/                           → Liste des candidatures
- POST   /applications/                           → Créer une candidature
- GET    /applications/{id}/                      → Détails
- PATCH  /applications/{id}/                      → Modifier statut
- DELETE /applications/{id}/                      → Retirer candidature

- GET    /applications/my_applications/           → Mes candidatures
- POST   /applications/{id}/update_status/        → Changer statut (recruteur)

RSVPS (Réponses événements):
- GET    /rsvps/                                  → Liste des RSVP
- POST   /rsvps/                                  → Créer/Modifier RSVP
- GET    /rsvps/{id}/                             → Détails
- DELETE /rsvps/{id}/                             → Annuler RSVP

- GET    /rsvps/my_rsvps/                         → Mes réponses

COMMENTS (Commentaires):
- GET    /comments/?post={id}                     → Commentaires d'un post
- POST   /comments/                               → Créer un commentaire
- GET    /comments/{id}/                          → Détails
- PUT    /comments/{id}/                          → Modifier
- DELETE /comments/{id}/                          → Supprimer

- GET    /comments/{id}/replies/                  → Réponses à un commentaire

REACTIONS (Réactions):
- GET    /reactions/?post={id}                    → Réactions d'un post
- POST   /reactions/                              → Créer une réaction
- DELETE /reactions/{id}/                         → Retirer une réaction

BOOKMARKS (Sauvegardes):
- GET    /bookmarks/                              → Liste des sauvegardes
- POST   /bookmarks/                              → Sauvegarder un post
- DELETE /bookmarks/{id}/                         → Retirer sauvegarde
"""