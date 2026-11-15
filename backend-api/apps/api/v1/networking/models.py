"""
G-Connect - Networking Models
Système de relations professionnelles : demandes de connexion (bidirectionnelles,
façon LinkedIn) et abonnements (follow, asymétriques, façon Twitter/Instagram).
"""

from django.db import models
from django.db.models import Q, F
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


class Connection(models.Model):
    """
    Demande de relation entre deux utilisateurs. `requester` envoie la demande
    à `addressee` ; une fois `accepted`, la relation est symétrique (visible
    dans les deux sens) sans dupliquer de ligne — voir `Connection.connected_ids`.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        ACCEPTED = "accepted", "Acceptée"
        DECLINED = "declined", "Refusée"

    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_connections")
    addressee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_connections")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(default=timezone.now)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["requester", "addressee"], name="unique_connection_pair"),
            models.CheckConstraint(check=~Q(requester=F("addressee")), name="connection_not_self"),
        ]
        indexes = [
            models.Index(fields=["addressee", "status"]),
            models.Index(fields=["requester", "status"]),
        ]

    def __str__(self):
        return f"{self.requester.username} -> {self.addressee.username} ({self.status})"

    def accept(self):
        self.status = self.Status.ACCEPTED
        self.responded_at = timezone.now()
        self.save(update_fields=["status", "responded_at"])

    def decline(self):
        self.status = self.Status.DECLINED
        self.responded_at = timezone.now()
        self.save(update_fields=["status", "responded_at"])

    @staticmethod
    def are_connected(user_a, user_b):
        return Connection.objects.filter(
            Q(requester=user_a, addressee=user_b) | Q(requester=user_b, addressee=user_a),
            status=Connection.Status.ACCEPTED,
        ).exists()

    @staticmethod
    def pending_between(user_a, user_b):
        """La demande en attente entre ces deux utilisateurs (quel que soit le
        sens), ou None. Sert à détecter le cas « double demande croisée »."""
        return Connection.objects.filter(
            Q(requester=user_a, addressee=user_b) | Q(requester=user_b, addressee=user_a),
            status=Connection.Status.PENDING,
        ).first()

    @staticmethod
    def connected_ids(user):
        """IDs des utilisateurs connectés (statut accepté) à `user`, dans les deux sens."""
        rows = Connection.objects.filter(
            Q(requester=user) | Q(addressee=user), status=Connection.Status.ACCEPTED
        ).values_list("requester_id", "addressee_id")
        ids = {uid for pair in rows for uid in pair}
        ids.discard(user.id)
        return ids


class Follow(models.Model):
    """Abonnement asymétrique — suivre un utilisateur sans relation réciproque."""

    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name="following_set")
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name="followers_set")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["follower", "following"], name="unique_follow_pair"),
            models.CheckConstraint(check=~Q(follower=F("following")), name="follow_not_self"),
        ]
        indexes = [
            models.Index(fields=["follower"]),
            models.Index(fields=["following"]),
        ]

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"
