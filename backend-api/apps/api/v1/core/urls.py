from django.urls import path
from .views import instance_identifier

urlpatterns = [
    path('', instance_identifier),
]