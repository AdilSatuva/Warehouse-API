"""
Models for the WarehouseAPI, defining the database structure for users, categories,
warehouses, products, stock movements, balances, transfers, orders, inventories,
notifications, and audit logs.
"""

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.utils import timezone

class User(AbstractUser):
    """
    Custom user model with roles for warehouse management.
    """
    ROLE_CHOICES = (
        ('admin', 'Administrator'),
        ('warehouse_manager', 'Warehouse Manager'),
        ('clerk', 'Clerk'),
        ('logistician', 'Logistician'),
        ('analyst', 'Analyst'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='clerk', verbose_name=_('Role'))

    class Meta:
        db_table = 'warehouse_user'
        verbose_name = _('User')
        verbose_name_plural = _('Users')

    def __str__(self):
        return self.username

class Category(models.Model):
    """
    Category model for organizing products, supporting hierarchical structure.
    """
    name = models.CharField(max_length=100, verbose_name=_('Name'))
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        verbose_name=_('Parent Category')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))

    class Meta:
        db_table = 'warehouse_category'
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')

    def __str__(self):
        return self.name

class Warehouse(models.Model):
    """
    Warehouse model with types and location information.
    """
    WAREHOUSE_TYPES = [
        ('retail', _('Retail')),
        ('distribution', _('Distribution')),
        ('storage', _('Storage')),
    ]
    name = models.CharField(max_length=100, verbose_name=_('Name'))
    type = models.CharField(max_length=20, choices=WAREHOUSE_TYPES, default='retail', verbose_name=_('Type'))
    location = models.CharField(max_length=200, verbose_name=_('Location'))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_warehouses',
        verbose_name=_('Created By')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))

    class Meta:
        db_table = 'warehouse_warehouse'
        verbose_name = _('Warehouse')
        verbose_name_plural = _('Warehouses')

    def __str__(self):
        return self.name

class Product(models.Model):
    """
    Product model with SKU, unit, and stock information.
    """
    name = models.CharField(max_length=100, verbose_name=_('Name'))
    sku = models.CharField(max_length=50, unique=True, verbose_name=_('SKU'))
    unit = models.CharField(max_length=20, verbose_name=_('Unit'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    min_stock = models.PositiveIntegerField(default=0, verbose_name=_('Minimum Stock'))
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name=_('Warehouse')
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name=_('Category')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))

    class Meta:
        db_table = 'warehouse_product'
        verbose_name = _('Product')
        verbose_name_plural = _('Products')

    def __str__(self):
        return self.name

class StockMovement(models.Model):
    """
    Records stock operations (in, out, transfer).
    """
    OPERATION_CHOICES = (
        ('in', _('Receipt')),
        ('out', _('Issue')),
        ('transfer', _('Transfer')),
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='stock_movements',
        verbose_name=_('Product')
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='stock_movements',
        verbose_name=_('Warehouse')
    )
    operation = models.CharField(max_length=20, choices=OPERATION_CHOICES, verbose_name=_('Operation'))
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)], verbose_name=_('Quantity'))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='stock_movements',
        verbose_name=_('Created By')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))

    class Meta:
        db_table = 'warehouse_stockmovement'
        verbose_name = _('Stock Movement')
        verbose_name_plural = _('Stock Movements')

    def __str__(self):
        return f"{self.operation} of {self.quantity} {self.product} in {self.warehouse}"

class StockBalance(models.Model):
    """
    Tracks current stock quantities per product and warehouse.
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='stock_balances',
        verbose_name=_('Product')
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='stock_balances',
        verbose_name=_('Warehouse')
    )
    quantity = models.PositiveIntegerField(default=0, verbose_name=_('Quantity'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))

    class Meta:
        db_table = 'warehouse_stockbalance'
        verbose_name = _('Stock Balance')
        verbose_name_plural = _('Stock Balances')
        unique_together = ('product', 'warehouse')

    def __str__(self):
        return f"{self.product} in {self.warehouse}: {self.quantity}"

class StockTransfer(models.Model):
    """
    Records stock transfers between warehouses.
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='transfers',
        verbose_name=_('Product')
    )
    from_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='transfers_from',
        verbose_name=_('From Warehouse')
    )
    to_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='transfers_to',
        verbose_name=_('To Warehouse')
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)], verbose_name=_('Quantity'))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='stock_transfers',
        verbose_name=_('Created By')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))

    class Meta:
        db_table = 'warehouse_stocktransfer'
        verbose_name = _('Stock Transfer')
        verbose_name_plural = _('Stock Transfers')

    def __str__(self):
        return f"{self.quantity} {self.product} from {self.from_warehouse} to {self.to_warehouse}"

class Order(models.Model):
    """
    Manages supply and shipment orders.
    """
    ORDER_TYPES = [
        ('supply', _('Supply')),
        ('shipment', _('Shipment')),
    ]
    STATUS_CHOICES = [
        ('new', _('New')),
        ('processing', _('Processing')),
        ('completed', _('Completed')),
    ]
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name=_('Product')
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)], verbose_name=_('Quantity'))
    type = models.CharField(max_length=20, choices=ORDER_TYPES, verbose_name=_('Type'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name=_('Status'))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='orders',
        verbose_name=_('Created By')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))

    class Meta:
        db_table = 'warehouse_order'
        verbose_name = _('Order')
        verbose_name_plural = _('Orders')

    def __str__(self):
        return f"{self.product} - {self.type} ({self.quantity})"

class Inventory(models.Model):
    """
    Records inventory checks with discrepancies.
    """
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='inventories',
        verbose_name=_('Warehouse')
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='inventories',
        verbose_name=_('Product')
    )
    recorded_quantity = models.PositiveIntegerField(default=0, verbose_name=_('Recorded Quantity'))
    actual_quantity = models.PositiveIntegerField(default=0, verbose_name=_('Actual Quantity'))
    discrepancy = models.IntegerField(verbose_name=_('Discrepancy'))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='inventories',
        verbose_name=_('Created By')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))

    class Meta:
        db_table = 'warehouse_inventory'
        verbose_name = _('Inventory')
        verbose_name_plural = _('Inventories')

    def save(self, *args, **kwargs):
        self.discrepancy = self.actual_quantity - self.recorded_quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Inventory for {self.product} in {self.warehouse}"

class Notification(models.Model):
    """
    Stores user notifications for various events.
    """
    NOTIFICATION_TYPES = [
        ('low_stock', _('Low Stock')),
        ('order', _('Order')),
        ('inventory', _('Inventory')),
        ('general', _('General')),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('User')
    )
    message = models.TextField(verbose_name=_('Message'))
    type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='general', verbose_name=_('Type'))
    is_read = models.BooleanField(default=False, verbose_name=_('Is Read'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))

    class Meta:
        db_table = 'warehouse_notification'
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')

    def __str__(self):
        return f"Notification for {self.user}: {self.message[:50]}"

class AuditLog(models.Model):
    """
    Logs user actions for auditing purposes.
    """
    action = models.CharField(max_length=100, verbose_name=_('Action'))
    model_name = models.CharField(max_length=100, default='unknown', verbose_name=_('Model Name'))
    object_id = models.PositiveIntegerField(null=True, blank=True, verbose_name=_('Object ID'))
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name=_('User')
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name=_('Created At'))
    details = models.TextField(blank=True, verbose_name=_('Details'))

    class Meta:
        db_table = 'warehouse_auditlog'
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')

    def __str__(self):
        return f"{self.action} on {self.model_name} ({self.object_id}) by {self.user or 'Anonymous'}"