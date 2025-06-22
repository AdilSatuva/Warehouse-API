from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator

class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', _('Admin')),
        ('warehouse_manager', _('Warehouse Manager')),
        ('clerk', _('Clerk')),
        ('logistician', _('Logistician')),
        ('analyst', _('Analyst')),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='clerk', verbose_name=_('Role'))
    
    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')

    def __str__(self):
        return self.username

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name=_('Name'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))

    class Meta:
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')

    def __str__(self):
        return self.name

class Warehouse(models.Model):
    WAREHOUSE_TYPES = [
        ('retail', _('Retail')),
        ('distribution', _('Distribution')),
        ('storage', _('Storage')),
    ]
    name = models.CharField(max_length=100, verbose_name=_('Name'))
    type = models.CharField(max_length=20, choices=WAREHOUSE_TYPES, default='retail', verbose_name=_('Type'))
    location = models.CharField(max_length=200, verbose_name=_('Location'))
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_warehouses', verbose_name=_('Created By'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))

    class Meta:
        verbose_name = _('Warehouse')
        verbose_name_plural = _('Warehouses')

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=100, verbose_name=_('Name'))
    sku = models.CharField(max_length=50, unique=True, verbose_name=_('SKU'))
    unit = models.CharField(max_length=20, verbose_name=_('Unit'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    min_stock = models.PositiveIntegerField(default=0, verbose_name=_('Minimum Stock'))
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='products', verbose_name=_('Warehouse'))
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))

    class Meta:
        verbose_name = _('Product')
        verbose_name_plural = _('Products')

    def __str__(self):
        return self.name

class StockMovement(models.Model):
    OPERATION_TYPES = [
        ('income', _('Income')),
        ('outcome', _('Outcome')),
    ]
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='movements', verbose_name=_('Product'))
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='movements', verbose_name=_('Warehouse'))
    operation = models.CharField(max_length=20, choices=OPERATION_TYPES, verbose_name=_('Operation'))
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)], verbose_name=_('Quantity'))
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='stock_movements', verbose_name=_('Created By'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))

    class Meta:
        verbose_name = _('Stock Movement')
        verbose_name_plural = _('Stock Movements')

    def __str__(self):
        return f"{self.product} - {self.operation} ({self.quantity})"

class StockBalance(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_balances', verbose_name=_('Product'))
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stock_balances', verbose_name=_('Warehouse'))
    total_quantity = models.PositiveIntegerField(default=0, verbose_name=_('Total Quantity'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))

    class Meta:
        verbose_name = _('Stock Balance')
        verbose_name_plural = _('Stock Balances')
        unique_together = ('product', 'warehouse')

    def __str__(self):
        return f"{self.product} in {self.warehouse}: {self.total_quantity}"

class StockTransfer(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='transfers', verbose_name=_('Product'))
    from_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='transfers_from', verbose_name=_('From Warehouse'))
    to_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='transfers_to', verbose_name=_('To Warehouse'))
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)], verbose_name=_('Quantity'))
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='stock_transfers', verbose_name=_('Created By'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))

    class Meta:
        verbose_name = _('Stock Transfer')
        verbose_name_plural = _('Stock Transfers')

    def __str__(self):
        return f"{self.product} from {self.from_warehouse} to {self.to_warehouse}"

class Order(models.Model):
    ORDER_TYPES = [
        ('supply', _('Supply')),
        ('shipment', _('Shipment')),
    ]
    STATUS_CHOICES = [
        ('new', _('New')),
        ('processing', _('Processing')),
        ('completed', _('Completed')),
    ]
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='orders', verbose_name=_('Product'))
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)], verbose_name=_('Quantity'))
    type = models.CharField(max_length=20, choices=ORDER_TYPES, verbose_name=_('Type'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name=_('Status'))
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='orders', verbose_name=_('Created By'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))

    class Meta:
        verbose_name = _('Order')
        verbose_name_plural = _('Orders')

    def __str__(self):
        return f"{self.product} - {self.type} ({self.quantity})"

class Inventory(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='inventories', verbose_name=_('Warehouse'))
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventories', verbose_name=_('Product'))
    recorded_quantity = models.PositiveIntegerField(default=0, verbose_name=_('Recorded Quantity'))
    actual_quantity = models.PositiveIntegerField(default=0, verbose_name=_('Actual Quantity'))
    discrepancy = models.IntegerField(verbose_name=_('Discrepancy'))
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='inventories', verbose_name=_('Created By'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))

    class Meta:
        verbose_name = _('Inventory')
        verbose_name_plural = _('Inventories')

    def save(self, *args, **kwargs):
        self.discrepancy = self.actual_quantity - self.recorded_quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Inventory for {self.product} in {self.warehouse}"

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications', verbose_name=_('User'))
    message = models.TextField(verbose_name=_('Message'))
    is_read = models.BooleanField(default=False, verbose_name=_('Is Read'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))

    class Meta:
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')

    def __str__(self):
        return f"Notification for {self.user}: {self.message[:50]}"

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('create', _('Create')),
        ('update', _('Update')),
        ('delete', _('Delete')),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='audit_logs', verbose_name=_('User'))
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name=_('Action'))
    model_name = models.CharField(max_length=100, verbose_name=_('Model Name'))
    object_id = models.CharField(max_length=100, verbose_name=_('Object ID'))
    details = models.TextField(blank=True, verbose_name=_('Details'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))

    class Meta:
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')

    def __str__(self):
        return f"{self.action} on {self.model_name} ({self.object_id}) by {self.user}"