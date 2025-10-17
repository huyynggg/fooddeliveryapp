from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, MerchantViewSet, CategoryViewSet, ProductViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'merchants', MerchantViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'products', ProductViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

