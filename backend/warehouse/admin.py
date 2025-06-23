"""
Admin configuration for the WarehouseAPI models.
"""

from django.contrib import admin
from warehouse.models import (
    User, Category, Warehouse, Product, StockMovement,
    StockBalance, StockTransfer, Order, Inventory, Notification, AuditLog
)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'role']
    list_filter = ['role']
    search_fields = ['username', 'email']

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name']

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'location', 'created_by', 'created_at']
    list_filter = ['type', 'created_at']
    search_fields = ['name', 'location']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'unit', 'warehouse', 'category', 'min_stock', 'created_at']
    list_filter = ['warehouse', 'category', 'created_at']
    search_fields = ['name', 'sku']

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['product', 'warehouse', 'operation', 'quantity', 'created_by', 'created_at']
    list_filter = ['operation', 'created_at']
    search_fields = ['product__name', 'warehouse__name']

@admin.register(StockBalance)
class StockBalanceAdmin(admin.ModelAdmin):
    list_display = ['product', 'warehouse', 'quantity', 'created_at', 'updated_at']
    list_filter = ['warehouse', 'created_at']
    search_fields = ['product__name', 'warehouse__name']

@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
    list_display = ['product', 'from_warehouse', 'to_warehouse', 'quantity', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['product__name', 'from_warehouse__name', 'to_warehouse__name']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['product', 'type', 'quantity', 'status', 'created_by', 'created_at']
    list_filter = ['type', 'status', 'created_at']
    search_fields = ['product__name']

@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ['product', 'warehouse', 'recorded_quantity', 'actual_quantity', 'discrepancy', 'created_by', 'created_at']
    list_filter = ['warehouse', 'created_at']
    search_fields = ['product__name', 'warehouse__name']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'message', 'type', 'is_read', 'created_at']
    list_filter = ['type', 'is_read', 'created_at']
    search_fields = ['message', 'user__username']

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'model_name', 'object_id', 'user', 'created_at']
    list_filter = ['action', 'model_name', 'created_at']
    search_fields = ['details', 'user__username']