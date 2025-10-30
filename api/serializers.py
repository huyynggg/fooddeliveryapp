from rest_framework import serializers
from .models import User, Merchant, Category, Product, Order, OrderItem, OrderStatusHistory, Notification
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'email'

    def validate(self, attrs):
        data = super().validate(attrs)

        data.update({
            'user_id': self.user.id,
            'name': self.user.name,
            'role': self.user.role,
            'status': self.user.status,
        })
        return data

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'phone']
        read_only_fields = ['id']
    
    def create(self, validated_data):
        # set server-defined defaults
        validated_data['role'] = 'customer'
        validated_data['status'] = 'pending'
        user = User.objects.create(**validated_data)
        user.is_active = False  # inactive until email activation
        user.save()
        return user

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'order', 'product', 'product_name', 'quantity', 'price', 'total_price']

class OrderStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source='changed_by.name', read_only=True)

    class Meta:
        model = OrderStatusHistory
        fields = ['id', 'previous_status', 'new_status', 'changed_by', 'changed_by_name', 'changed_at']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    courier_name = serializers.CharField(source='courier.name', read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'customer', 'merchant', 'courier', 'status', 'subtotal', 'fee', 'total', 'created_at', 'items', 'courier_name', 'status_history']

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'message', 'is_read', 'created_at']

class MerchantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Merchant
        fields = '__all__'
        read_only_fields = ['id', 'user', 'created_at', 'rating', 'status', 'is_open']

    def create(self, validated_data):
        # assign the current user as the merchant owner
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)