from django.contrib import admin
from .models import User, Warehouse, Category, Product, Movement, Transfer, Order, Inventory, Notification, AuditLog

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'role']
    list_filter = ['role']
    search_fields = ['username', 'email']

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'location', 'created_at', 'updated_at']
    list_filter = ['type', 'created_at']
    search_fields = ['name', 'location']

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'quantity', 'warehouse', 'category', 'created_by', 'created_at']
    list_filter = ['warehouse', 'category', 'created_at']
    search_fields = ['name', 'sku']

@admin.register(Movement)
class MovementAdmin(admin.ModelAdmin):
    list_display = ['product', 'warehouse', 'quantity', 'operation', 'performed_by', 'timestamp']
    list_filter = ['operation', 'timestamp', 'performed_by']
    search_fields = ['product__name', 'warehouse__name']

@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ['product', 'from_warehouse', 'to_warehouse', 'quantity', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['product__name', 'from_warehouse__name', 'to_warehouse__name']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['type', 'product', 'quantity', 'status', 'created_by', 'created_at']
    list_filter = ['type', 'status', 'created_at']
    search_fields = ['product__name']

@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ['product', 'warehouse', 'actual_quantity', 'recorded_quantity', 'discrepancy', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['product__name', 'warehouse__name']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'message', 'type', 'is_read', 'created_at']
    list_filter = ['type', 'is_read', 'created_at']
    search_fields = ['message']

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'model', 'timestamp']
    list_filter = ['action', 'timestamp']
    search_fields = ['action', 'model']