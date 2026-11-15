"""E59 | MFA Superadmin moderation desk.

A dedicated, bounded read model and confirmed decisions for existing Reports.
No migrations, no access to applicant files, no automatic bans/deletions and no
change to the mobile ReportViewSet.
"""
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.api.v1.backoffice.models import Report
from apps.api.v1.core.audit import log_audit_event
from apps.api.v1.core.permissions import IsSuperAdmin
from apps.api.v1.core.responses import error_response, success_response
from apps.api.v1.users.web_authentication import EstablishmentWebTokenAuthentication

STATUSES = {"all", "pending", "dismissed", "actioned"}
TARGETS = {"all", "post", "comment", "user"}
REASONS = {choice for choice, _ in Report.Reason.choices}


def _target_kind(report):
    return "post" if report.post_id else "comment" if report.comment_id else "user"


def _target_description(report):
    if report.post_id:
        return report.post.title
    if report.comment_id:
        return "Commentaire · " + (report.comment.content or "")[:155]
    if report.reported_user_id:
        return report.reported_user.get_full_name().strip() or report.reported_user.username
    return "Élément indisponible"


def _entry(report):
    target = _target_kind(report)
    author = report.reporter
    reviewer = report.reviewed_by
    return {
        "id": report.pk,
        "reason": report.reason,
        "reason_display": report.get_reason_display(),
        "description": report.description[:1200],
        "status": report.status,
        "status_display": report.get_status_display(),
        "target": target,
        "target_id": report.post_id or report.comment_id or report.reported_user_id,
        "target_title": _target_description(report),
        "target_excerpt": (
            (report.post.content or "")[:250] if report.post_id else
            (report.comment.content or "")[:250] if report.comment_id else ""
        ),
        "organisation": (
            report.post.institution.name if report.post_id and report.post.institution_id else
            report.comment.post.institution.name
            if report.comment_id and report.comment.post.institution_id else ""
        ),
        "reported_by": author.get_full_name().strip() or author.username,
        "reviewed_by": (
            reviewer.get_full_name().strip() or reviewer.username if reviewer else None
        ),
        "created_at": report.created_at.isoformat(),
        "reviewed_at": report.reviewed_at.isoformat() if report.reviewed_at else None,
        "is_hidden": bool(report.post.is_hidden_by_admin) if report.post_id else False,
        "critical": report.reason in (
            Report.Reason.HARASSMENT, Report.Reason.HATE_SPEECH,
        ),
        "can_dismiss": report.status == Report.Status.PENDING,
        "can_hide": (
            report.status == Report.Status.PENDING
            and report.post_id is not None
            and not report.post.is_hidden_by_admin
        ),
    }


def _query():
    return Report.objects.select_related(
        "reporter", "reported_user", "post", "post__institution",
        "comment", "comment__post", "comment__post__institution",
        "reviewed_by",
    )


class _ModerationBase(APIView):
    authentication_classes = [EstablishmentWebTokenAuthentication]
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    @staticmethod
    def reply(message, payload):
        response = success_response(message, payload)
        response["Cache-Control"] = "no-store"
        return response


class SuperadminModerationDirectoryE59(_ModerationBase):
    """GET case register and real global moderation counters."""

    def get(self, request):
        status = str(request.query_params.get("status", "pending")).strip()
        reason = str(request.query_params.get("reason", "all")).strip()
        target = str(request.query_params.get("target", "all")).strip()
        search = str(request.query_params.get("search", "")).strip()[:120]
        if (status not in STATUSES or reason not in REASONS | {"all"}
                or target not in TARGETS):
            return error_response("Filtres de modération invalides.", status_code=400)
        try:
            page = int(request.query_params.get("page", "1"))
            size = int(request.query_params.get("page_size", "10"))
        except (TypeError, ValueError):
            return error_response("Pagination invalide.", status_code=400)
        if page < 1 or not 1 <= size <= 50:
            return error_response("Pagination invalide.", status_code=400)

        all_reports = Report.objects.all()
        month_ago = timezone.now() - timedelta(days=30)
        summary = all_reports.aggregate(
            total=Count("pk"),
            pending=Count("pk", filter=Q(status=Report.Status.PENDING)),
            resolved=Count("pk", filter=Q(status__in=(
                Report.Status.DISMISSED, Report.Status.ACTIONED,
            ))),
            reviewed_30d=Count("pk", filter=Q(
                reviewed_at__gte=month_ago,
                status__in=(Report.Status.DISMISSED, Report.Status.ACTIONED),
            )),
            critical_pending=Count("pk", filter=Q(
                status=Report.Status.PENDING,
                reason__in=(Report.Reason.HARASSMENT, Report.Reason.HATE_SPEECH),
            )),
            dismissed=Count("pk", filter=Q(status=Report.Status.DISMISSED)),
            actioned=Count("pk", filter=Q(status=Report.Status.ACTIONED)),
        )
        by_reason = {
            choice: all_reports.filter(status=Report.Status.PENDING, reason=choice).count()
            for choice in REASONS
        }

        qs = _query()
        if status != "all":
            qs = qs.filter(status=status)
        if reason != "all":
            qs = qs.filter(reason=reason)
        if target == "post":
            qs = qs.filter(post__isnull=False)
        elif target == "comment":
            qs = qs.filter(comment__isnull=False)
        elif target == "user":
            qs = qs.filter(reported_user__isnull=False)
        if search:
            qs = qs.filter(
                Q(post__title__icontains=search)
                | Q(post__content__icontains=search)
                | Q(comment__content__icontains=search)
                | Q(reported_user__username__icontains=search)
                | Q(reporter__username__icontains=search)
                | Q(description__icontains=search)
            )

        count = qs.count()
        pages = max(1, (count + size - 1) // size)
        if page > pages:
            return error_response("Page inexistante.", status_code=404)
        entries = qs.order_by("-created_at", "-pk")[(page - 1) * size:page * size]
        return self.reply("Registre réel de modération.", {
            "summary": summary, "by_reason": by_reason,
            "count": count, "page": page, "pages": pages, "page_size": size,
            "results": [_entry(report) for report in entries],
        })


class SuperadminModerationDecisionE59(_ModerationBase):
    """POST /backoffice/moderation-v2/<id>/decision/
    {
      "decision": "dismiss" | "hide_post",
      "confirmation": "CONFIRMER",
      "reason": "...",   # mandatory for hide_post
    }
    """

    def post(self, request, pk):
        action = request.data.get("decision")
        confirmation = request.data.get("confirmation")
        reason = str(request.data.get("reason", "") or "").strip()
        if action not in {"dismiss", "hide_post"}:
            return error_response("Décision inconnue.", status_code=400)
        if confirmation != "CONFIRMER":
            return error_response("Confirmation explicite obligatoire.", status_code=400)
        if action == "hide_post" and not 10 <= len(reason) <= 255:
            return error_response(
                "Précisez le motif de masquage (10 à 255 caractères).", status_code=400,
            )

        with transaction.atomic():
            report = _query().select_for_update().filter(pk=pk).first()
            if report is None:
                return error_response("Signalement introuvable.", status_code=404)
            if report.status != Report.Status.PENDING:
                return error_response("Ce signalement a déjà été traité.", status_code=409)
            if action == "hide_post":
                if report.post_id is None:
                    return error_response(
                        "Le masquage est réservé aux signalements de publication.",
                        status_code=400,
                    )
                if report.post.is_hidden_by_admin:
                    return error_response("Cette publication est déjà masquée.", status_code=409)
                post = report.post
                post.is_hidden_by_admin = True
                post.hidden_reason = reason
                post.save(update_fields=["is_hidden_by_admin", "hidden_reason"])
                log_audit_event(
                    "post_hidden", user=request.user, request=request,
                    metadata={
                        "report_id": report.pk, "post_id": report.post_id,
                        "reason": reason,
                    },
                )
                report.status = Report.Status.ACTIONED
            else:
                report.status = Report.Status.DISMISSED

            report.reviewed_by = request.user
            report.reviewed_at = timezone.now()
            report.save(update_fields=["status", "reviewed_by", "reviewed_at"])
            log_audit_event(
                "report_reviewed", user=request.user, request=request,
                metadata={
                    "report_id": report.pk, "outcome": report.status,
                    "post_id": report.post_id,
                },
            )
            result = _entry(report)
        return self.reply("Décision enregistrée.", result)
