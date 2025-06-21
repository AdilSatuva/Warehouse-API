from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.files.base import ContentFile
from io import BytesIO
import qrcode
from django.utils import timezone

class User(AbstractUser):
    role = models.CharField(max_length=50, choices=[
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('clerk', 'Clerk'),
        ('warehouse_manager', 'Warehouse Manager'),
        ('logistician', 'Logistician'),
        ('analyst', 'Analyst'),
    ], default='clerk')

    def __str__(self):
        return self.username

class Category(models.Model):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Warehouse(models.Model):
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50, choices=[
        ('retail', 'Retail'),
        ('wholesale', 'Wholesale'),
        ('reserve', 'Reserve'),
        ('raw_material', 'Raw Material'),
        ('transit', 'Transit'),
    ])
    location = models.CharField(max_length=200)  # Required for admin
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # Required for admin

    def __str__(self):
        return f"{self.name} ({self.type})"

class Product(models.Model):
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=50, unique=True)
    unit = models.CharField(max_length=50)
    min_stock = models.PositiveIntegerField(default=0)
    quantity = models.PositiveIntegerField(default=0)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, null=True, on_delete=models.SET_NULL)
    description = models.TextField(blank=True)
    qr_code = models.ImageField(upload_to='qr_codes/', null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Save first to generate ID
        if not self.qr_code:
            qr = qrcode.QRCode()
            qr.add_data(f'http://localhost:8000/api/products/{self.id}')
            qr.make()
            img = qr.make_image(fill='black', back_color='white')
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            self.qr_code.save(f'qr_{self.sku}.png', ContentFile(buffer.getvalue()))
            super().save(*args, **kwargs)  # Save again to update qr_code

    def __str__(self):
        return f"{self.name} ({self.sku})"

class Movement(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    operation = models.CharField(max_length=20, choices=[('income', 'Income'), ('outcome', 'Outcome')])
    quantity = models.PositiveIntegerField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='performed_movements')  # Required for admin
    timestamp = models.DateTimeField(default=timezone.now)  # Required for admin

    def __str__(self):
        return f"{self.operation} - {self.product.name} ({self.quantity})"

class Transfer(models.Model):
    from_warehouse = models.ForeignKey(Warehouse, related_name='transfers_from', on_delete=models.CASCADE)
    to_warehouse = models.ForeignKey(Warehouse, related_name='transfers_to', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transfer {self.product.name} from {self.from_warehouse} to {self.to_warehouse}"

class Order(models.Model):
    type = models.CharField(max_length=20, choices=[('supply', 'Supply'), ('shipment', 'Shipment')])
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=[('new', 'New'), ('processing', 'Processing'), ('completed', 'Completed')])
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} - {self.product.name}"

class Inventory(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    recorded_quantity = models.PositiveIntegerField()
    actual_quantity = models.PositiveIntegerField()
    discrepancy = models.IntegerField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Inventory for {self.product.name}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    type = models.CharField(max_length=50, choices=[
        ('low_stock', 'Low Stock'),
        ('order_completed', 'Order Completed'),
        ('error', 'Error'),
    ])
    is_read = models.BooleanField(default=False)  # Required for admin
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.message[:50]

class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    object_id = models.CharField(max_length=50, null=True)
    timestamp = models.DateTimeField(default=timezone.now)
    details = models.TextField(null=True)

    def __str__(self):
        return f"{self.action} on {self.model} by {self.user}"
