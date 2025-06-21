from celery import shared_task
from django.core.mail import send_mail
from warehouse.models import Product, Notification
from django.conf import settings
import csv
from io import StringIO

@shared_task
def export_stock_balance_to_csv(user_id, stock_data):
    """Экспорт данных о балансе склада в CSV."""
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Product ID', 'Product Name', 'Warehouse', 'Quantity'])
    for item in stock_data:
        writer.writerow([
            item['product'],
            item['product__name'],
            item['warehouse__name'],
            item['total_quantity']
        ])
    csv_content = output.getvalue()
    output.close()

    # Отправка CSV по email
    send_mail(
        subject='Stock Balance CSV Export',
        message='Attached is the stock balance CSV file.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.DEFAULT_FROM_EMAIL],
        fail_silently=False,
        html_message=None,
        attachments=[('stock_balance.csv', csv_content, 'text/csv')]
    )
    return csv_content

@shared_task
def notify_low_stock():
    """Уведомление о низком уровне запасов."""
    low_stock_products = Product.objects.filter(quantity__lte=models.F('min_stock'))
    for product in low_stock_products:
        Notification.objects.create(
            user=product.created_by,
            message=f"Low stock for {product.name} in {product.warehouse.name}. Current quantity: {product.quantity}"
        )