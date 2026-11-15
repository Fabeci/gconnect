# backoffice/models.py
"""
Signalements (posts, commentaires, utilisateurs) — alimente la file de
modération du back-office superAdmin. Un signalement cible exactement un
élément (validé dans le serializer plutôt qu'en contrainte SQL, pour un
message d'erreur clair côté client).
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class Report(models.Model):
    class Reason(models.TextChoices):
        SPAM = "spam", "Spam"
        HARASSMENT = "harassment", "Harcèlement"
        HATE_SPEECH = "hate_speech", "Discours haineux"
        INAPPROPRIATE = "inappropriate", "Contenu inapproprié"
        FAKE_INFO = "fake_info", "Fausse information"
        OTHER = "other", "Autre"

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        DISMISSED = "dismissed", "Rejeté"
        ACTIONED = "actioned", "Action prise"

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports_filed",
    )
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True,
        related_name="reports_received",
    )
    post = models.ForeignKey(
        "posts.Post", on_delete=models.CASCADE, null=True, blank=True, related_name="reports",
    )
    comment = models.ForeignKey(
        "posts.Comment", on_delete=models.CASCADE, null=True, blank=True, related_name="reports",
    )
    reason = models.CharField(max_length=20, choices=Reason.choices)
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reports_reviewed",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "-created_at"])]

    def __str__(self):
        return f"Signalement #{self.id} ({self.get_reason_display()}) — {self.get_status_display()}"

    @property
    def target_label(self):
        if self.reported_user_id:
            return f"Utilisateur : {self.reported_user}"
        if self.post_id:
            return f"Publication #{self.post_id}"
        if self.comment_id:
            return f"Commentaire #{self.comment_id}"
        return "—"


class ImportJob(models.Model):
    """
    Trace un import CSV/Excel massif (étudiants, alumni, promotions,
    établissements) — traitement synchrone ligne par ligne, chaque ligne
    dans sa propre transaction (une erreur n'annule pas les lignes déjà
    importées). `errors`/`created_rows` alimentent le rapport détaillé.
    """
    class ImportType(models.TextChoices):
        STUDENTS = "students", "Étudiants"
        ALUMNI = "alumni", "Alumni"
        PROMOTIONS = "promotions", "Promotions"
        ESTABLISHMENTS = "establishments", "Établissements"

    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="import_jobs",
    )
    institution = models.ForeignKey(
        "establishments.Institution", on_delete=models.SET_NULL, null=True, blank=True,
    )
    import_type = models.CharField(max_length=20, choices=ImportType.choices)
    file_name = models.CharField(max_length=255)
    total_rows = models.PositiveIntegerField(default=0)
    success_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    errors = models.JSONField(default=list, blank=True)
    created_rows = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Import {self.get_import_type_display()} — {self.success_count}/{self.total_rows} ({self.created_at})"
