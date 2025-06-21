from django.test import TestCase
from rest_framework.test import APIClient
from .models import User, Warehouse, Product, Movement
from django.urls import reverse

class WarehouseAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(username='admin', password='admin123', role='admin')
        self.warehouse = Warehouse.objects.create(name='Main', location='Moscow')
        self.product = Product.objects.create(
            name='Keyboard', sku='KB001', unit='pcs', min_stock=10, warehouse=self.warehouse
        )
        self.client.login(username='admin', password='admin123')

    def test_create_product(self):
        data = {
            'name': 'Mouse',
            'sku': 'MS001',
            'unit': 'pcs',
            'min_stock': 5,
            'warehouse': self.warehouse.id
        }
        response = self.client.post(reverse('product_list_create'), data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Product.objects.count(), 2)

    def test_stock_movement(self):
        data = {
            'product': self.product.id,
            'warehouse': self.warehouse.id,
            'operation': 'income',
            'quantity': 20
        }
        response = self.client.post(reverse('stock_income'), data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Movement.objects.count(), 1)

    def test_low_stock(self):
        response = self.client.get(reverse('low_stock'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('Keyboard', str(response.data))