from django.contrib import admin
from django.conf import settings 
from django.urls import path, include
from django.http import JsonResponse 
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.permissions import AllowAny, IsAdminUser
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from api.views import ActivateAccountView

def home(request):
    return JsonResponse({
        "message": "Food Delivery API is running",
        "endpoints": {
            "users": "/api/v1/users/",
            "merchants": "/api/v1/merchants/",
            "categories": "/api/v1/categories/",
            "products": "/api/v1/products/",
            "orders": "/api/v1/orders/",
            "tokens": "/api/v1/token/"
        }
    })

urlpatterns = [
    path('api/schema/', SpectacularAPIView.as_view(
        permission_classes=[AllowAny if settings.DEBUG else IsAdminUser]
    ), name='schema'),

    path('api/docs/', SpectacularSwaggerView.as_view(
        url_name='schema',
        permission_classes=[AllowAny if settings.DEBUG else IsAdminUser]
    ), name='swagger-ui'),

    path('', home),
    path('admin/', admin.site.urls),
    path('api/v1/', include('api.urls')),
    path('api/v1/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/activate/<uidb64>/<token>', ActivateAccountView.as_view(), name='activate')

]


