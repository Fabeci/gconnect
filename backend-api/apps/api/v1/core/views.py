import socket
from django.http import HttpResponse

def instance_identifier(request):
    return HttpResponse(f"Served from: {socket.gethostname()}")
