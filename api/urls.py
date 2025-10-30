from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, MerchantViewSet, CategoryViewSet, ProductViewSet, OrderViewSet, OrderItemViewSet, OrderStatusHistoryViewSet, NotificationViewSet, ActivateAccountView

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'merchants', MerchantViewSet, basename= 'merchant')
router.register(r'categories', CategoryViewSet)
router.register(r'products', ProductViewSet)
router.register(r'orders', OrderViewSet)
router.register(r'order-items', OrderItemViewSet)
router.register(r'status-history', OrderStatusHistoryViewSet) 
router.register(r'notifications', NotificationViewSet)


urlpatterns = [
    path('', include(router.urls)),
    path('activate/<uidb64>/<token>/', ActivateAccountView.as_view(), name='activate')
]

urlpatterns+=router.urls 


