# ai/views.py
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.api.v1.core.responses import error_response, success_response
from apps.api.v1.posts.serializers import PostListSerializer

from .providers import get_ai_provider


class HashtagSuggestionView(APIView):
    """POST /ai/hashtags/  {text} → {hashtags: [...]}"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        text = (request.data.get("text") or "").strip()
        if len(text) < 5:
            return error_response("Texte trop court (5 caractères minimum).", status_code=400)
        provider = get_ai_provider()
        hashtags = provider.suggest_hashtags(text)
        return success_response("Suggestions générées.", {"hashtags": hashtags})


class SummarizeView(APIView):
    """POST /ai/summarize/  {text} → {summary}"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        text = (request.data.get("text") or "").strip()
        if len(text) < 20:
            return error_response("Texte trop court (20 caractères minimum).", status_code=400)
        provider = get_ai_provider()
        summary = provider.summarize(text)
        return success_response("Résumé généré.", {"summary": summary})


class ImproveWritingView(APIView):
    """POST /ai/improve/  {text} → {suggestions: [...]}"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        text = (request.data.get("text") or "").strip()
        if len(text) < 5:
            return error_response("Texte trop court (5 caractères minimum).", status_code=400)
        provider = get_ai_provider()
        result = provider.improve_writing(text)
        return success_response("Analyse terminée.", result)


class ContentRecommendationsView(APIView):
    """GET /ai/recommendations/ → publications recommandées."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        provider = get_ai_provider()
        posts = provider.recommend_posts(request.user, limit=10)
        data = PostListSerializer(posts, many=True, context={"request": request}).data
        return success_response("Recommandations générées.", data)
