from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse 

def home(request):
    return JsonResponse({"message": "Food Delivery API is running", "docs": "/api/"})
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('api.urls')),
]

