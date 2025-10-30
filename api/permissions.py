from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdmin(BasePermission):
    """Allow only users with role='admin'."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.role == 'admin')

class IsVendor(BasePermission):
    """Allow only users with role='vendor'."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.role == 'vendor')

class IsCourier(BasePermission):
    """Allow only couriers."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.role == 'courier')

class IsCustomer(BasePermission):
    """Allow only customers."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.role == 'customer')

class ReadOnly(BasePermission):
    """Allow GET, HEAD, OPTIONS for everyone."""
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS

class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        # Admins can always do anything
        if request.user.role == 'admin':
            return True

        # Vendors: can only modify their own merchant or product
        if hasattr(obj, 'user'):  # Merchant model
            return obj.user == request.user

        if hasattr(obj, 'merchant'):  # Category, Product
            return obj.merchant.user == request.user 

        # Customers: can only view their own orders
        if hasattr(obj, 'customer'):
            return obj.customer == request.user

        return False
    
class IsCourier(BasePermission):
    #Allow couriers to access only their assigned orders.
    def has_permission(self, request, view):
        return bool(request.user and request.user.role == 'courier')
    #Couriers can view and update orders assigned to them 
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admim':
            return True
        if hasattr(obj, 'courier') and obj.courier == request.user:
            return True 
        return request.method in SAFE_METHODS #allow safe reads for testing
    
class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user == obj.user or getattr(request.user, 'role', None) == 'admin'
        