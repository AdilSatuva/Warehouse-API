from drf_yasg import openapi

warehouse_example = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID склада'),
        'name': openapi.Schema(type=openapi.TYPE_STRING, description='Название склада'),
        'location': openapi.Schema(type=openapi.TYPE_STRING, description='Местоположение'),
        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, description='Дата создания'),
    },
    example={
        'id': 1,
        'name': 'Главный склад',
        'location': 'Москва',
        'created_at': '2025-06-20T12:00:00Z'
    }
)

product_example = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID товара'),
        'name': openapi.Schema(type=openapi.TYPE_STRING, description='Название товара'),
        'sku': openapi.Schema(type=openapi.TYPE_STRING, description='Артикул'),
        'unit': openapi.Schema(type=openapi.TYPE_STRING, description='Единица измерения'),
        'description': openapi.Schema(type=openapi.TYPE_STRING, description='Описание'),
        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, description='Дата создания'),
        'min_stock': openapi.Schema(type=openapi.TYPE_INTEGER, description='Минимальный запас'),
        'warehouse': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID склада'),
        'warehouse_name': openapi.Schema(type=openapi.TYPE_STRING, description='Название склада'),
    },
    example={
        'id': 1,
        'name': 'Клавиатура',
        'sku': 'KB001',
        'unit': 'pcs',
        'description': 'Механическая клавиатура',
        'created_at': '2025-06-20T12:00:00Z',
        'min_stock': 10,
        'warehouse': 1,
        'warehouse_name': 'Главный склад'
    }
)

movement_example = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID движения'),
        'product': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID товара'),
        'product_name': openapi.Schema(type=openapi.TYPE_STRING, description='Название товара'),
        'warehouse': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID склада'),
        'warehouse_name': openapi.Schema(type=openapi.TYPE_STRING, description='Название склада'),
        'operation': openapi.Schema(type=openapi.TYPE_STRING, enum=['income', 'outcome'], description='Тип операции'),
        'quantity': openapi.Schema(type=openapi.TYPE_INTEGER, description='Количество'),
        'performed_by': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID пользователя'),
        'performed_by_username': openapi.Schema(type=openapi.TYPE_STRING, description='Имя пользователя'),
        'timestamp': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, description='Время операции'),
    },
    example={
        'id': 1,
        'product': 1,
        'product_name': 'Клавиатура',
        'warehouse': 1,
        'warehouse_name': 'Главный склад',
        'operation': 'income',
        'quantity': 10,
        'performed_by': 1,
        'performed_by_username': 'admin',
        'timestamp': '2025-06-20T15:23:56Z'
    }
)

audit_log_example = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID записи'),
        'user': openapi.Schema(type=openapi.TYPE_INTEGER, nullable=True, description='ID пользователя'),
        'action': openapi.Schema(type=openapi.TYPE_STRING, description='Действие'),
        'model': openapi.Schema(type=openapi.TYPE_STRING, description='Модель'),
        'object_id': openapi.Schema(type=openapi.TYPE_INTEGER, nullable=True, description='ID объекта'),
        'timestamp': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, description='Время действия'),
        'details': openapi.Schema(type=openapi.TYPE_STRING, description='Детали'),
    },
    example={
        'id': 1,
        'user': 1,
        'action': 'created',
        'model': 'Product',
        'object_id': 1,
        'timestamp': '2025-06-20T12:23:56Z',
        'details': 'Product: Keyboard'
    }
)