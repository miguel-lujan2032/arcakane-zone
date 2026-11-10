from django.http import JsonResponse


def health(request):
    """Endpoint mínimo para health checks de Render."""
    return JsonResponse({"status": "ok"})
