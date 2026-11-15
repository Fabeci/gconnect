"""E57 · Read-only global catalogue for Superadmin: real posts, offers and events.

The regular mobile posts API is audience-filtered and cannot serve as an
unrestricted moderation inventory. This endpoint requires a privileged,
MFA-verified professional WebToken. No publishing or moderation side effects.
"""
from django.db.models import Count, Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.api.v1.backoffice.models import Report
from apps.api.v1.core.permissions import IsSuperAdmin
from apps.api.v1.core.responses import error_response, success_response
from apps.api.v1.posts.models import Post
from apps.api.v1.users.web_authentication import EstablishmentWebTokenAuthentication


def _public_state(post):
    if post.is_hidden_by_admin:
        return "hidden"
    if post.is_draft:
        return "draft"
    if post.is_archived:
        return "archived"
    return "published"


class SuperadminContentDirectoryE57(APIView):
    """GET /api/v1/backoffice/content-directory/?type=&state=&search=&page=&page_size="""

    authentication_classes = [EstablishmentWebTokenAuthentication]
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        post_type = str(request.query_params.get("type", "all")).strip()
        state = str(request.query_params.get("state", "all")).strip()
        search = str(request.query_params.get("search", "")).strip()[:120]
        valid_types = {key for key, _ in Post.PostType.choices}
        if post_type not in valid_types | {"all"} or state not in {
            "all", "published", "draft", "hidden", "archived",
        }:
            return error_response("Filtre de contenus invalide.", status_code=400)
        try:
            page = int(request.query_params.get("page", "1"))
            size = int(request.query_params.get("page_size", "12"))
        except (TypeError, ValueError):
            return error_response("Pagination invalide.", status_code=400)
        if page < 1 or size < 1 or size > 50:
            return error_response("Pagination invalide.", status_code=400)

        all_posts = Post.objects.all()
        aggregated = all_posts.aggregate(
            total=Count("pk"),
            opportunities=Count("pk", filter=Q(post_type=Post.PostType.OPPORTUNITY)),
            events=Count("pk", filter=Q(post_type=Post.PostType.EVENT)),
            projects=Count("pk", filter=Q(post_type=Post.PostType.PROJECT)),
            discussions=Count("pk", filter=Q(post_type__in=(
                Post.PostType.DISCUSSION, Post.PostType.SHARE,
            ))),
            hidden=Count("pk", filter=Q(is_hidden_by_admin=True)),
            drafts=Count("pk", filter=Q(is_draft=True, is_hidden_by_admin=False)),
            archived=Count("pk", filter=Q(
                is_archived=True, is_draft=False, is_hidden_by_admin=False,
            )),
            published=Count("pk", filter=Q(
                is_hidden_by_admin=False, is_draft=False, is_archived=False,
            )),
        )
        aggregated["reports_pending"] = Report.objects.filter(
            status=Report.Status.PENDING
        ).count()

        query = all_posts
        if post_type != "all":
            query = query.filter(post_type=post_type)
        if state == "hidden":
            query = query.filter(is_hidden_by_admin=True)
        elif state == "draft":
            query = query.filter(is_hidden_by_admin=False, is_draft=True)
        elif state == "archived":
            query = query.filter(
                is_hidden_by_admin=False, is_draft=False, is_archived=True,
            )
        elif state == "published":
            query = query.filter(
                is_hidden_by_admin=False, is_draft=False, is_archived=False,
            )
        if search:
            query = query.filter(
                Q(title__icontains=search)
                | Q(content__icontains=search)
                | Q(author__username__icontains=search)
                | Q(author__first_name__icontains=search)
                | Q(author__last_name__icontains=search)
                | Q(institution__name__icontains=search)
                | Q(opportunity__enterprise__company_name__icontains=search)
            )

        count = query.count()
        pages = max(1, (count + size - 1) // size)
        if page > pages:
            return error_response("Page inexistante.", status_code=404)

        records = list(
            query.select_related("author", "institution", "opportunity__enterprise")
            .order_by("-created_at", "-pk")[(page - 1) * size:page * size]
        )
        ids = [item.pk for item in records]
        reported = {
            row["post_id"]: row["count"]
            for row in Report.objects.filter(
                post_id__in=ids, status=Report.Status.PENDING,
            ).values("post_id").annotate(count=Count("pk"))
        }
        results = []
        for post in records:
            opportunity = getattr(post, "opportunity", None)
            enterprise = getattr(opportunity, "enterprise", None) if opportunity else None
            organisation = (
                enterprise.company_name if enterprise
                else post.institution.name if post.institution else None
            )
            author = post.author
            author_name = author.get_full_name().strip() or author.username
            description = post.content or ""
            results.append({
                "id": post.pk,
                "title": post.title,
                "description": description[:3000],
                "excerpt": description[:200],
                "type": post.post_type,
                "type_label": post.get_post_type_display(),
                "state": _public_state(post),
                "audience": post.audience,
                "author_name": author_name,
                "organisation": organisation,
                "views": post.views_count,
                "comments": post.comments_count,
                "reactions": post.reactions_count,
                "pending_reports": reported.get(post.pk, 0),
                "created_at": post.created_at.isoformat(),
                "opportunity": ({
                    "category": opportunity.category,
                    "status": opportunity.status,
                    "deadline": opportunity.deadline.isoformat() if opportunity.deadline else None,
                } if opportunity else None),
            })

        response = success_response("Contenus réels de la plateforme.", {
            "summary": aggregated,
            "count": count,
            "pages": pages,
            "page": page,
            "page_size": size,
            "results": results,
        })
        response["Cache-Control"] = "no-store"
        return response
