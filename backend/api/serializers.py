from rest_framework import serializers
from warehouse.models import User, Category, Warehouse, Product, Movement, Transfer, Order, Inventory, Notification, AuditLog

class UserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source='role', default='clerk')  # Используйте role напрямую

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role']

class AssignRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=[('admin', 'Admin'), ('manager', 'Manager'), ('clerk', 'Clerk')])

class CategorySerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField()
    parent = serializers.StringRelatedField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'parent', 'created_by', 'created_at']

class WarehouseSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField()

    class Meta:
        model = Warehouse
        fields = ['id', 'name', 'type', 'location', 'created_by', 'created_at', 'updated_at']

class ProductSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()
    warehouse = serializers.StringRelatedField()
    created_by = serializers.StringRelatedField()
    qr_code = serializers.ImageField(required=False, allow_null=True)
    quantity = serializers.IntegerField(source='get_quantity', read_only=True)
    class Meta:
        model = Product
        fields = ['id', 'name', 'sku', 'unit', 'min_stock', 'quantity', 'warehouse', 'category', 'description', 'qr_code', 'created_by', 'created_at']

class MovementSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    warehouse = serializers.PrimaryKeyRelatedField(queryset=Warehouse.objects.all())
    created_by = serializers.StringRelatedField()
    performed_by = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Movement
        fields = ['id', 'product', 'warehouse', 'operation', 'quantity', 'created_by', 'created_at', 'performed_by', 'timestamp']

class StockBalanceSerializer(serializers.Serializer):
    product = serializers.IntegerField(required=False)
    product__name = serializers.CharField(required=False, source='name')
    warehouse__name = serializers.CharField(required=False, source='warehouse_name')
    total_quantity = serializers.IntegerField(required=False)
    id = serializers.IntegerField(required=False)
    sku = serializers.CharField(required=False)
    current_stock = serializers.IntegerField(required=False)
    min_stock = serializers.IntegerField(required=False)

class TransferSerializer(serializers.ModelSerializer):
    from_warehouse = serializers.PrimaryKeyRelatedField(queryset=Warehouse.objects.all())
    to_warehouse = serializers.PrimaryKeyRelatedField(queryset=Warehouse.objects.all())
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    created_by = serializers.StringRelatedField()

    class Meta:
        model = Transfer
        fields = ['id', 'from_warehouse', 'to_warehouse', 'product', 'quantity', 'created_by', 'created_at']

class OrderSerializer(serializers.ModelSerializer):
    product = serializers.StringRelatedField()
    created_by = serializers.StringRelatedField()

    class Meta:
        model = Order
        fields = ['id', 'type', 'product', 'quantity', 'status', 'created_by', 'created_at']

class InventorySerializer(serializers.ModelSerializer):
    warehouse = serializers.StringRelatedField()
    product = serializers.StringRelatedField()
    created_by = serializers.StringRelatedField()

    class Meta:
        model = Inventory
        fields = ['id', 'warehouse', 'product', 'recorded_quantity', 'actual_quantity', 'discrepancy', 'created_by', 'created_at']

class NotificationSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = Notification
        fields = ['id', 'user', 'message', 'type', 'is_read', 'created_at']

class AuditLogSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = AuditLog
        fields = ['id', 'user', 'action', 'model', 'object_id', 'timestamp', 'details']