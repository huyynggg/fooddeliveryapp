from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from api.models import User, Merchant, Product, Order

class PermissionTests(TestCase):
    def setUp(self):
        # Create users
        self.admin = User.objects.create_user(email='admin@test.com', password='admin123', role='admin', name='Admin')
        self.vendor = User.objects.create_user(email='vendor@test.com', password='vendor123', role='vendor', name='Vendor')
        self.customer = User.objects.create_user(email='customer@test.com', password='cust123', role='customer', name='Customer')
        self.courier = User.objects.create_user(email='courier@test.com', password='cour123', role='courier', name='Courier')

        # Create merchant owned by vendor
        self.merchant = Merchant.objects.create(name="Vendor's Shop", user=self.vendor, city="Dubai")

        # Create product under that merchant
        self.product = Product.objects.create(category=None, name="Test Product", description="Nice food", price=10.00, unit="pcs", stock=5, is_available=True)

        # Create an order by the customer
        self.order = Order.objects.create(customer=self.customer, merchant=self.merchant, total=20.00, fee=2.00)

        # Assign courier to order
        self.order.courier = self.courier
        self.order.save()

        # API client setup
        self.client = APIClient()

    def auth(self, user):
        """Helper method to authenticate a user."""
        self.client.force_authenticate(user=user)

    # ---------- TESTS ----------

    def test_admin_can_access_anything(self):
        self.auth(self.admin)
        response = self.client.get(f'/api/v1/orders/{self.order.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_vendor_can_only_see_own_merchant_orders(self):
        self.auth(self.vendor)
        response = self.client.get(f'/api/v1/orders/{self.order.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)  # belongs to vendor’s merchant

        # Create another merchant + order (not vendor’s)
        other_vendor = User.objects.create_user(email='othervendor@test.com', password='test', role='vendor', name='Other')
        other_merchant = Merchant.objects.create(name="Other Shop", user=other_vendor, city="Riyadh")
        other_order = Order.objects.create(customer=self.customer, merchant=other_merchant, total=10.00, fee=1.00)

        response = self.client.get(f'/api/v1/orders/{other_order.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_customer_can_only_see_their_own_orders(self):
        self.auth(self.customer)
        response = self.client.get(f'/api/v1/orders/{self.order.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Another customer tries
        other_customer = User.objects.create_user(email='fake@test.com', password='123', role='customer', name='Imposter')
        self.auth(other_customer)
        response = self.client.get(f'/api/v1/orders/{self.order.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_courier_can_only_access_assigned_orders(self):
        self.auth(self.courier)
        response = self.client.get(f'/api/v1/orders/{self.order.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Another courier tries to access it
        other_courier = User.objects.create_user(email='othercourier@test.com', password='123', role='courier', name='Other')
        self.auth(other_courier)
        response = self.client.get(f'/api/v1/orders/{self.order.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
