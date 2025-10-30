from rest_framework import viewsets, status, filters, views, permissions
from .models import User, Merchant, Category, Product, Order, OrderItem, OrderStatusHistory, Notification
from .serializers import UserSerializer, MerchantSerializer, CategorySerializer, ProductSerializer, OrderSerializer, OrderItemSerializer, OrderStatusHistorySerializer, NotificationSerializer, MerchantSerializer 
from .permissions import IsVendor, IsAdmin, ReadOnly, IsOwnerOrAdmin
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action 
from rest_framework.response import Response 
from django_filters.rest_framework import DjangoFilterBackend
from django.core.mail import send_mail
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site
from api.utils.tokens import account_activation_token
from django.shortcuts import get_object_or_404
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.conf import settings 
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import EmailTokenObtainPairSerializer


class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer

def send_activation_email(request, user):
    token = account_activation_token.make_token(user)
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    activation_link = f"{settings.SITE_URL}/api/v1/activate/{uidb64}/{token}/"

    subject = "Activate your account"
    message = f"""
    Hi {user.name},

    Thanks for signing up! Please click the link below to activate your account:
    {activation_link}

    If you didn’t create this account, just ignore this email.
    """

    send_mail(
        subject,
        message,
        'no-reply@fooddelivery.com',
        [user.email],
        fail_silently=False,
    )

def get_permissions(self):
    if self.action == 'create':
        return [AllowAny()]
    return [IsAuthenticated()]

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        user = serializer.save(is_active=False)
        send_activation_email(self.request, user)

class ActivateAccountView(views.APIView):
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user and account_activation_token.check_token(user, token):
            user.is_active = True
            user.save()
            return Response({'message': 'Account activated successfully!'}, status=status.HTTP_200_OK)
        return Response({'error': 'Invalid or expired activation link'}, status=status.HTTP_400_BAD_REQUEST)

class MerchantViewSet(viewsets.ModelViewSet):
    queryset = Merchant.objects.all()
    serializer_class = MerchantSerializer
    permission_classes = [IsAuthenticated, IsVendor | IsAdmin | ReadOnly, IsOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]  
    filterset_fields = ['merchant_type', 'city', 'status']
    search_fields = ['name', 'description', 'city']
    ordering_fields = ['rating', 'delivery_fee', 'prep_time_avg']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Merchant.objects.all()
        elif user.role == 'vendor':
            return Merchant.objects.filter(user=user)
        return Merchant.objects.filter(status='active')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user) 

    def get_queryset(self):
        user = self.request.user
        # Admins can see all merchants; vendors only see their own
        if user.is_authenticated and user.role in ['vendor', 'admin']:
            return Merchant.objects.filter(user=user) if user.role == 'vendor' else Merchant.objects.all()
        # Customers see only open & approved merchants
        return Merchant.objects.filter(is_open=True, status='approved')

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, IsVendor | IsAdmin | ReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Category.objects.all()
        elif user.role == 'vendor':
            return Category.objects.filter(merchant__user=user)
        return Category.objects.none()

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, IsVendor | IsAdmin | ReadOnly, IsOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_available', 'category__merchant__city']
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'stock']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Product.objects.all()
        elif user.role == 'vendor':
            return Product.objects.filter(category__merchant__user=user)
        return Product.objects.filter(is_available=True)

    
class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer 
    permission_classes = [IsAuthenticated, IsVendor | IsAdmin | ReadOnly]

    def update(self, request, *args, **kwargs):
        user = request.user
        instance = self.get_object()
        instance._updated_by = user

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Order.objects.all()
        elif user.role == 'vendor':
            return Order.objects.filter(merchant__user = user)
        elif user.role == 'customer':
            return Order.objects.filter(customer=user)
        elif user.role == 'courier':
            return Order.objects.filter(courier=user)
        return Order.objects.none()
        
    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)

class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer 
    permission_classes = [IsAuthenticated, IsVendor | IsAdmin | ReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return OrderItem.objects.all()
        elif user.role == 'customer':
            return OrderItem.objects.filter(order__customer=user)
        elif user.role == 'vendor':
            return OrderItem.objects.filter(order__merchant__user=user)
        return OrderItem.objects.none()
    
class OrderStatusHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OrderStatusHistory.objects.all().select_related('order', 'changed_by')
    serializer_class = OrderStatusHistorySerializer
    permission_classes = [IsAuthenticated, IsAdmin | ReadOnly]

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only show notifications for the logged-in user
        return Notification.objects.filter(recipient=self.request.user).order_by('-created_at')

    def perform_update(self, serializer):
        # mark notifications as read
        serializer.save(is_read=True)

    def mark_all_as_read(self, request):
        """Mark all notifications as read for the logged-in user."""
        user = request.user
        updated_count = Notification.objects.filter(recipient=user, is_read=False).update(is_read=True)
        return Response(
            {"message": f"{updated_count} notifications marked as read."},
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['delete'])
    def clear_all(self, request):
        """Delete all notifications for the logged-in user."""
        user = request.user
        deleted_count, _ = Notification.objects.filter(recipient=user).delete()
        return Response(
            {"message": f"{deleted_count} notifications deleted."},
            status=status.HTTP_200_OK
    )

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({"unread_count": count})
    
class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_read']  # allow filtering by read/unread

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).order_by('-created_at')    
