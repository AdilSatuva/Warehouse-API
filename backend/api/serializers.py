"""
Serializers for the WarehouseAPI, converting model instances to JSON.
"""

from rest_framework import serializers
from warehouse.models import (
    User, Category, Warehouse, Product, StockMovement,
    StockBalance, StockTransfer, Order, Inventory, Notification, AuditLog
)
import logging

logger = logging.getLogger(__name__)

class UserSerializer(serializers.ModelSerializer):
    """
    Serializes User model for API responses.
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role']

class AssignRoleSerializer(serializers.Serializer):
    """
    Serializes role assignment data.
    """
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES)

class CategorySerializer(serializers.ModelSerializer):
    """
    Serializes Category model, including created_by and parent fields.
    """
    created_by = UserSerializer(read_only=True)
    parent = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), allow_null=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'parent', 'created_by', 'created_at']

class WarehouseSerializer(serializers.ModelSerializer):
    """
    Serializes Warehouse model, including created_by field.
    """
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = Warehouse
        fields = ['id', 'name', 'type', 'location', 'created_by', 'created_at', 'updated_at']

class ProductSerializer(serializers.ModelSerializer):
    """
    Serializes Product model, including related category and warehouse.
    """
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', allow_null=True, write_only=True
    )
    warehouse = WarehouseSerializer(read_only=True)
    warehouse_id = serializers.PrimaryKeyRelatedField(
        queryset=Warehouse.objects.all(), source='warehouse', write_only=True
    )
    total_quantity = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'sku', 'unit', 'min_stock', 'warehouse', 'warehouse_id',
            'category', 'category_id', 'description', 'created_at', 'total_quantity'
        ]
        read_only_fields = ['id', 'created_at', 'total_quantity']

class ProductCreateSerializer(serializers.ModelSerializer):
    """
    Serializes Product creation data, ensuring unique SKU.
    """
    class Meta:
        model = Product
        fields = ['name', 'sku', 'unit', 'description', 'min_stock', 'warehouse', 'category']

    def validate_sku(self, value):
        if Product.objects.filter(sku=value).exists():
            logger.error(f"Duplicate SKU detected: {value}")
            raise serializers.ValidationError("SKU must be unique.")
        return value

class StockMovementSerializer(serializers.ModelSerializer):
    """
    Serializes StockMovement model for stock operations.
    """
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    warehouse = serializers.PrimaryKeyRelatedField(queryset=Warehouse.objects.all())
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = StockMovement
        fields = ['id', 'product', 'warehouse', 'operation', 'quantity', 'created_by', 'created_at']

class StockBalanceSerializer(serializers.ModelSerializer):
    """
    Serializes StockBalance model for current stock quantities.
    """
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    product__name = serializers.CharField(source='product.name', read_only=True)
    warehouse = serializers.PrimaryKeyRelatedField(queryset=Warehouse.objects.all())
    warehouse__name = serializers.CharField(source='warehouse.name', read_only=True)

    class Meta:
        model = StockBalance
        fields = ['id', 'product', 'product__name', 'warehouse', 'warehouse__name', 'quantity']
        read_only_fields = ['id', 'product__name', 'warehouse__name']

class StockTransferSerializer(serializers.ModelSerializer):
    """
    Serializes StockTransfer model for transfers between warehouses.
    """
    from_warehouse = serializers.PrimaryKeyRelatedField(queryset=Warehouse.objects.all())
    to_warehouse = serializers.PrimaryKeyRelatedField(queryset=Warehouse.objects.all())
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = StockTransfer
        fields = ['id', 'from_warehouse', 'to_warehouse', 'product', 'quantity', 'created_by', 'created_at']

class OrderSerializer(serializers.ModelSerializer):
    """
    Serializes Order model for supply and shipment orders.
    """
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'type', 'product', 'quantity', 'status', 'created_by', 'created_at']

class InventorySerializer(serializers.ModelSerializer):
    """
    Serializes Inventory model for stock checks.
    """
    warehouse = serializers.PrimaryKeyRelatedField(queryset=Warehouse.objects.all())
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = Inventory
        fields = ['id', 'warehouse', 'product', 'recorded_quantity', 'actual_quantity', 'discrepancy', 'created_by', 'created_at']

class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializes Notification model for user notifications.
    """
    user = UserSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'user', 'message', 'type', 'is_read', 'created_at']

class AuditLogSerializer(serializers.ModelSerializer):
    """
    Serializes AuditLog model for action logging.
    """
    user = UserSerializer(read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'user', 'action', 'model_name', 'object_id', 'created_at', 'details']