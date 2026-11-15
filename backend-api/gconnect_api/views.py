from django.http import JsonResponse

def landing_page(request):
    return JsonResponse({
        "success": True,
        "message": "Bienvenue sur l’API G-Connect. Veuillez utiliser /api/v1/ pour accéder aux endpoints."
    })
