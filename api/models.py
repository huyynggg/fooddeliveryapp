from django.db import models
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver 
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager


class CustomUserManager(BaseUserManager):
    def create_user(self, email, name, phone, role='customer', password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, phone=phone, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, phone, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, name, phone, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('vendor', 'Vendor'),
        ('courier', 'Courier'),
        ('admin', 'Admin'),
    ]

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    status = models.CharField(max_length=50, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name', 'phone']

    def __str__(self):
        return self.email


class Merchant(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='merchants')
    name = models.CharField(max_length=255)
    merchant_type = models.CharField(max_length=50)  # restaurant, grocery
    description = models.TextField(blank=True)
    city = models.CharField(max_length=100)
    is_open = models.BooleanField(default=True)
    status = models.CharField(max_length=50, default='active')

    def __str__(self):
        return self.name


class Category(models.Model):
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=20, default='pcs')
    stock = models.IntegerField(default=0)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('out_for_delivery', 'Out for delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    customer = models.ForeignKey('User', on_delete=models.CASCADE, related_name='orders')
    merchant = models.ForeignKey('Merchant', on_delete=models.CASCADE, related_name='orders')
    courier = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='deliveries')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} ({self.customer.name})"
    
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # unit price
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

class OrderStatusHistory(models.Model):
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='status_history')
    previous_status = models.CharField(max_length=50, null=True, blank=True)
    new_status = models.CharField(max_length=50)
    changed_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.order.id}: {self.previous_status} → {self.new_status}"


class Notification(models.Model):
    recipient = models.ForeignKey('User', on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"To {self.recipient.name}: {self.message[:40]}"


    @receiver(pre_save, sender=Order)
    def notify_order_status_change(sender, instance, **kwargs):
        if not instance.pk:
            return  # ignore brand new orders
        try:
            previous = Order.objects.get(pk=instance.pk)
        except Order.DoesNotExist:
            return

    # Only act if the status actually changed
        if previous.status != instance.status:
            message = f"Your order #{instance.id} status changed from '{previous.status}' to '{instance.status}'."

        # Notify the customer
        Notification.objects.create(
            recipient=instance.customer,
            message=message
        )

        # Notify the courier (if assigned)
        if instance.courier:
            Notification.objects.create(
                recipient=instance.courier,
                message=f"Order #{instance.id} updated to '{instance.status}'."
            )

        # Notify the vendor (merchant owner)
        if instance.merchant.user:
            Notification.objects.create(
                recipient=instance.merchant.user,
                message=f"Order #{instance.id} status is now '{instance.status}'."
            )

    @receiver(pre_save, sender=Order)
    def log_order_status_change(sender, instance, **kwargs):
        """Track and log when order status changes."""
        if not instance.pk:
            return  # New order, no previous status yet
        try:
            previous = Order.objects.get(pk=instance.pk)
        except Order.DoesNotExist:
            return
        if previous.status != instance.status:
        # Create a status history record
            OrderStatusHistory.objects.create(
            order=instance,
            previous_status=previous.status,
            new_status=instance.status,
            changed_by=getattr(instance, '_updated_by', None)
        )