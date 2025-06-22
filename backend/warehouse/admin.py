from django.contrib import admin
from .models import Product, Warehouse, StockMovement, StockBalance, StockTransfer, Order, Inventory, Category, Notification, AuditLog
from django.utils.translation import gettext_lazy as _

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'get_quantity', 'warehouse', 'min_stock', 'category')
    list_filter = ('warehouse', 'category', 'min_stock')
    search_fields = ('name', 'sku', 'description')
    list_editable = ('min_stock',)
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('name',)
    
    def get_quantity(self, obj):
        """
        Display the total quantity of the product across all warehouses.
        Fetches from StockBalance or calculates based on StockMovement if StockBalance is not available.
        """
        try:
            # Assuming StockBalance stores the total quantity per product
            balance = StockBalance.objects.filter(product=obj).aggregate(total_quantity=Sum('total_quantity'))
            return balance['total_quantity'] or 0
        except Exception:
            # Fallback: Calculate from StockMovement (income - outcome)
            income = StockMovement.objects.filter(product=obj, operation='income').aggregate(total=Sum('quantity'))['total'] or 0
            outcome = StockMovement.objects.filter(product=obj, operation='outcome').aggregate(total=Sum('quantity'))['total'] or 0
            return income - outcome
    get_quantity.short_description = _('Quantity')

    def get_queryset(self, request):
        """Optimize queryset to reduce database hits."""
        qs = super().get_queryset(request)
        return qs.select_related('warehouse', 'category')

    def has_change_permission(self, request, obj=None):
        """Restrict changes to admin and warehouse_manager roles."""
        if request.user.is_superuser or request.user.groups.filter(name='admin').exists():
            return True
        if obj and request.user.groups.filter(name='warehouse_manager').exists():
            return True
        return False

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'location', 'created_by', 'created_at')
    list_filter = ('type', 'location')
    search_fields = ('name', 'location')
    readonly_fields = ('created_at', 'updated_at')
    
    def has_change_permission(self, request, obj=None):
        """Restrict changes to admin and warehouse_manager roles."""
        if request.user.is_superuser or request.user.groups.filter(name='admin').exists():
            return True
        if obj and request.user.groups.filter(name='warehouse_manager').exists():
            return True
        return False

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('product', 'warehouse', 'operation', 'quantity', 'created_at')
    list_filter = ('operation', 'warehouse', 'created_at')
    search_fields = ('product__name', 'product__sku')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(StockBalance)
class StockBalanceAdmin(admin.ModelAdmin):
    list_display = ('product', 'warehouse', 'total_quantity')
    list_filter = ('warehouse',)
    search_fields = ('product__name', 'product__sku')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
    list_display = ('product', 'from_warehouse', 'to_warehouse', 'quantity', 'created_at')
    list_filter = ('from_warehouse', 'to_warehouse', 'created_at')
    search_fields = ('product__name', 'product__sku')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'type', 'status', 'created_at')
    list_filter = ('type', 'status', 'created_at')
    search_fields = ('product__name', 'product__sku')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('warehouse', 'product', 'recorded_quantity', 'actual_quantity', 'discrepancy')
    list_filter = ('warehouse',)
    search_fields = ('product__name', 'product__sku')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('message', 'user__username')
    readonly_fields = ('created_at',)

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'model_name', 'object_id', 'created_at')
    list_filter = ('action', 'model_name', 'created_at')
    search_fields = ('user__username', 'details')
    readonly_fields = ('created_at',)