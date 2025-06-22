import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.pagination import PageNumberPagination
from django.db.models import Sum, F, Case, When, IntegerField, Q
from django_filters.rest_framework import DjangoFilterBackend
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.views.decorators.cache import never_cache
from django.core.cache import cache
from warehouse.models import Product, StockMovement, Warehouse, User, AuditLog, Category, Inventory, Notification, StockTransfer, Order
from api.serializers import (
    UserSerializer, AssignRoleSerializer, WarehouseSerializer, CategorySerializer,
    ProductSerializer, StockMovementSerializer, StockBalanceSerializer, InventorySerializer,
    NotificationSerializer, AuditLogSerializer, StockTransferSerializer, OrderSerializer
)
from api.tasks import export_stock_balance_to_csv, notify_low_stock

logger = logging.getLogger(__name__)

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class CanManageProducts(permissions.BasePermission):
    def has_permission(self, request, view):
        is_allowed = request.user.is_authenticated and request.user.role in ['admin', 'warehouse_manager', 'clerk']
        logger.info(f"Checking permissions for user: {request.user.username}, role: {request.user.role}, authenticated: {request.user.is_authenticated}, allowed: {is_allowed}")
        return is_allowed

class LoginView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        logger.info(f"Login attempt for username: {request.data.get('username')}")
        try:
            response = super().post(request, *args, **kwargs)
            user = User.objects.get(username=request.data['username'])
            response.data['role'] = user.role
            logger.info(f"User logged in: {user.username}, role: {user.role}")
            return response
        except User.DoesNotExist:
            logger.error(f"Login failed: User {request.data.get('username')} not found")
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

class UserProfileView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

class UserListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        users = User.objects.all()
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(users, request)
        serializer = UserSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        if request.user.role != 'admin':
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            logger.info(f"User created: {serializer.data['username']} by {request.user.username}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserAssignRoleView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if request.user.role != 'admin':
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            user = User.objects.get(pk=pk)
            serializer = AssignRoleSerializer(data=request.data)
            if serializer.is_valid():
                user.role = serializer.validated_data['role']
                user.save()
                logger.info(f"Role assigned: {user.username} to {user.role} by {request.user.username}")
                return Response(UserSerializer(user).data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

class WarehouseListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @method_decorator(cache_page(60*10))
    def get(self, request):
        logger.info(f"Warehouse list requested by {request.user.username}")
        warehouses = Warehouse.objects.all()
        search = request.query_params.get('search')
        if search:
            warehouses = warehouses.filter(Q(name__icontains=search) | Q(location__icontains=search))
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(warehouses, request)
        serializer = WarehouseSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @method_decorator(never_cache)
    def post(self, request):
        if request.user.role not in ['admin', 'warehouse_manager']:
            logger.warning(f"User {request.user.username} attempted to create warehouse without permission")
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        serializer = WarehouseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            logger.info(f"Warehouse created: {serializer.data['name']} by {request.user.username}")
            cache.delete_pattern('warehouse_list*')
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        logger.error(f"Warehouse creation failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class WarehouseDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            warehouse = Warehouse.objects.get(pk=pk)
            serializer = WarehouseSerializer(warehouse)
            return Response(serializer.data)
        except Warehouse.DoesNotExist:
            return Response({"error": "Warehouse not found"}, status=status.HTTP_404_NOT_FOUND)

    @method_decorator(never_cache)
    def put(self, request, pk):
        if request.user.role != 'admin':
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            warehouse = Warehouse.objects.get(pk=pk)
            serializer = WarehouseSerializer(warehouse, data=request.data)
            if serializer.is_valid():
                serializer.save()
                logger.info(f"Warehouse updated: {warehouse.name} by {request.user.username}")
                cache.delete_pattern('warehouse_list*')
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Warehouse.DoesNotExist:
            return Response({"error": "Warehouse not found"}, status=status.HTTP_404_NOT_FOUND)

    @method_decorator(never_cache)
    def delete(self, request, pk):
        if request.user.role != 'admin':
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            warehouse = Warehouse.objects.get(pk=pk)
            warehouse.delete()
            logger.info(f"Warehouse deleted: {warehouse.name} by {request.user.username}")
            cache.delete_pattern('warehouse_list*')
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Warehouse.DoesNotExist:
            return Response({"error": "Warehouse not found"}, status=status.HTTP_404_NOT_FOUND)

class WarehouseProductsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    @method_decorator(cache_page(60))
    def get(self, request, pk):
        try:
            warehouse = Warehouse.objects.get(pk=pk)
            products = Product.objects.filter(warehouse=warehouse)
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(products, request)
            serializer = ProductSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        except Warehouse.DoesNotExist:
            return Response({"error": "Warehouse not found"}, status=status.HTTP_404_NOT_FOUND)

class CategoryListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @method_decorator(cache_page(60*10))
    def get(self, request):
        categories = Category.objects.all()
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(categories, request)
        serializer = CategorySerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @method_decorator(never_cache)
    def post(self, request):
        if request.user.role not in ['admin', 'warehouse_manager']:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            logger.info(f"Category created: {serializer.data['name']} by {request.user.username}")
            cache.delete_pattern('category_list*')
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CategoryDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            category = Category.objects.get(pk=pk)
            serializer = CategorySerializer(category)
            return Response(serializer.data)
        except Category.DoesNotExist:
            return Response({"error": "Category not found"}, status=status.HTTP_404_NOT_FOUND)

    @method_decorator(never_cache)
    def put(self, request, pk):
        if request.user.role not in ['admin', 'warehouse_manager']:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            category = Category.objects.get(pk=pk)
            serializer = CategorySerializer(category, data=request.data)
            if serializer.is_valid():
                serializer.save()
                logger.info(f"Category updated: {category.name} by {request.user.username}")
                cache.delete_pattern('category_list*')
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Category.DoesNotExist:
            return Response({"error": "Category not found"}, status=status.HTTP_404_NOT_FOUND)

    @method_decorator(never_cache)
    def delete(self, request, pk):
        if request.user.role != 'admin':
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            category = Category.objects.get(pk=pk)
            category.delete()
            logger.info(f"Category deleted: {category.name} by {request.user.username}")
            cache.delete_pattern('category_list*')
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Category.DoesNotExist:
            return Response({"error": "Category not found"}, status=status.HTTP_404_NOT_FOUND)

class ProductListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [CanManageProducts]
    pagination_class = StandardResultsSetPagination

    @method_decorator(cache_page(60))
    def get(self, request):
        products = Product.objects.all()
        category_id = request.query_params.get('category_id')
        if category_id and category_id.isdigit():
            products = products.filter(category_id=category_id)
        search = request.query_params.get('search')
        if search:
            products = products.filter(Q(name__icontains=search) | Q(sku__icontains=search))
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(products, request)
        serializer = ProductSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @method_decorator(never_cache)
    def post(self, request):
        logger.info(f"Product creation attempt by {request.user.username}: {request.data}")
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            logger.info(f"Product created: {serializer.data['name']} by {request.user.username}")
            cache.delete_pattern('product_list*')
            notify_low_stock.delay()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        logger.error(f"Product creation failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ProductDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
            serializer = ProductSerializer(product)
            return Response(serializer.data)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

    @method_decorator(never_cache)
    def put(self, request, pk):
        if request.user.role not in ['admin', 'warehouse_manager']:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            product = Product.objects.get(pk=pk)
            serializer = ProductSerializer(product, data=request.data)
            if serializer.is_valid():
                serializer.save()
                logger.info(f"Product updated: {product.name} by {request.user.username}")
                cache.delete_pattern('product_list*')
                notify_low_stock.delay()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

    @method_decorator(never_cache)
    def delete(self, request, pk):
        if request.user.role != 'admin':
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            product = Product.objects.get(pk=pk)
            product.delete()
            logger.info(f"Product deleted: {product.name} by {request.user.username}")
            cache.delete_pattern('product_list*')
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

class StockIncomeOutcomeView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @method_decorator(never_cache)
    def post(self, request):
        if request.user.role not in ['admin', 'warehouse_manager', 'clerk']:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        data = request.data.copy()
        data['created_by'] = request.user.id
        serializer = StockMovementSerializer(data=data)
        if serializer.is_valid():
            product = Product.objects.get(id=data['product'])
            if data['operation'] == 'outcome':
                balance = StockMovement.objects.filter(product=product, warehouse=data['warehouse']).aggregate(
                    total=Sum(F('quantity') * Case(
                        When(operation='income', then=1),
                        When(operation='outcome', then=-1),
                        output_field=IntegerField()
                    ))
                )['total'] or 0
                if balance < data['quantity']:
                    return Response({"error": "Insufficient stock"}, status=status.HTTP_400_BAD_REQUEST)
            serializer.save()
            logger.info(f"Stock {data['operation']}: {product.name} ({data['quantity']}) by {request.user.username}")
            cache.delete_pattern('stock_movements*')
            cache.delete_pattern('stock_balance*')
            notify_low_stock.delay()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class StockMovementsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['product', 'warehouse', 'operation', 'created_at']
    pagination_class = StandardResultsSetPagination

    @method_decorator(cache_page(60*5))
    def get(self, request, product_id=None):
        movements = StockMovement.objects.all()
        if product_id:
            movements = movements.filter(product_id=product_id)
        warehouse_id = request.query_params.get('warehouse_id')
        if warehouse_id and warehouse_id.isdigit():
            movements = movements.filter(warehouse_id=warehouse_id)
        if 'operation' in request.query_params:
            movements = movements.filter(operation=request.query_params['operation'])
        if 'date_start' in request.query_params:
            movements = movements.filter(created_at__gte=request.query_params['date_start'])
        if 'date_end' in request.query_params:
            movements = movements.filter(created_at__lte=request.query_params['date_end'])
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(movements, request)
        serializer = StockMovementSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

class StockBalanceView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    @method_decorator(cache_page(60*5))
    def get(self, request, product_id=None):
        movements = StockMovement.objects.all()
        if product_id:
            movements = movements.filter(product_id=product_id)
        warehouse_id = request.query_params.get('warehouse_id')
        if warehouse_id and warehouse_id.isdigit():
            movements = movements.filter(warehouse_id=warehouse_id)
        balances = movements.values(
            'product', 'product__name', 'warehouse__name'
        ).annotate(
            total_quantity=Sum(F('quantity') * Case(
                When(operation='income', then=1),
                When(operation='outcome', then=-1),
                output_field=IntegerField()
            ))
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(balances, request)
        serializer = StockBalanceSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

class LowStockView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    @method_decorator(cache_page(60*5))
    def get(self, request):
        try:
            products = Product.objects.all()
            warehouse_id = request.query_params.get('warehouse_id')
            if warehouse_id and warehouse_id.isdigit():
                products = products.filter(warehouse_id=warehouse_id)
            low_stock_products = []
            for product in products:
                try:
                    if not product.warehouse:
                        logger.warning(f"Product {product.name} has no warehouse assigned")
                        continue
                    balance = StockMovement.objects.filter(product=product, warehouse=product.warehouse).aggregate(
                        total=Sum(F('quantity') * Case(
                            When(operation='income', then=1),
                            When(operation='outcome', then=-1),
                            output_field=IntegerField()
                        ))
                    )['total'] or 0
                    if balance < getattr(product, 'min_stock', 0):
                        low_stock_products.append({
                            'id': product.id,
                            'name': product.name,
                            'sku': product.sku,
                            'current_stock': balance,
                            'min_stock': getattr(product, 'min_stock', 0),
                            'warehouse_name': product.warehouse.name if product.warehouse else 'Unknown'
                        })
                except Exception as e:
                    logger.error(f"Error processing product {product.id}: {str(e)}")
                    continue
            serializer = StockBalanceSerializer(low_stock_products, many=True)
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(serializer.data, request)
            return paginator.get_paginated_response(page)
        except Exception as e:
            logger.error(f"LowStockView error: {str(e)}")
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StockTransferListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role not in ['admin', 'warehouse_manager', 'logistician']:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        transfers = StockTransfer.objects.all()
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(transfers, request)
        serializer = StockTransferSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        if request.user.role not in ['admin', 'warehouse_manager', 'logistician']:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        serializer = StockTransferSerializer(data=request.data)
        if serializer.is_valid():
            product = Product.objects.get(id=request.data['product'])
            balance = StockMovement.objects.filter(product=product, warehouse=request.data['from_warehouse']).aggregate(
                total=Sum(F('quantity') * Case(
                    When(operation='income', then=1),
                    When(operation='outcome', then=-1),
                    output_field=IntegerField()
                ))
            )['total'] or 0
            if balance < request.data['quantity']:
                return Response({"error": "Insufficient stock in source warehouse"}, status=status.HTTP_400_BAD_REQUEST)
            serializer.save(created_by=request.user)
            logger.info(f"Transfer created: {product.name} ({request.data['quantity']}) from {request.data['from_warehouse']} to {request.data['to_warehouse']} by {request.user.username}")
            notify_low_stock.delay()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class StockTransferDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        if request.user.role not in ['admin', 'warehouse_manager', 'logistician']:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            transfer = StockTransfer.objects.get(pk=pk)
            serializer = StockTransferSerializer(transfer)
            return Response(serializer.data)
        except StockTransfer.DoesNotExist:
            return Response({"error": "Transfer not found"}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk):
        if request.user.role not in ['admin', 'warehouse_manager', 'logistician']:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            transfer = StockTransfer.objects.get(pk=pk)
            serializer = StockTransferSerializer(transfer, data=request.data)
            if serializer.is_valid():
                serializer.save()
                logger.info(f"Transfer updated: {transfer.id} by {request.user.username}")
                notify_low_stock.delay()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except StockTransfer.DoesNotExist:
            return Response({"error": "Transfer not found"}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        if request.user.role != 'admin':
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            transfer = StockTransfer.objects.get(pk=pk)
            transfer.delete()
            logger.info(f"Transfer deleted: {transfer.id} by {request.user.username}")
            return Response(status=status.HTTP_204_NO_CONTENT)
        except StockTransfer.DoesNotExist:
            return Response({"error": "Transfer not found"}, status=status.HTTP_404_NOT_FOUND)

class OrderListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role not in ['admin', 'warehouse_manager', 'logistician']:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        orders = Order.objects.all()
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(orders, request)
        serializer = OrderSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        if request.user.role not in ['admin', 'warehouse_manager', 'logistician']:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        serializer = OrderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            logger.info(f"Order created: {serializer.data['id']} by {request.user.username}")
            notify_low_stock.delay()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OrderDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        if request.user.role not in ['admin', 'warehouse_manager', 'logistician']:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            order = Order.objects.get(pk=pk)
            serializer = OrderSerializer(order)
            return Response(serializer.data)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk):
        if request.user.role not in ['admin', 'warehouse_manager', 'logistician']:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            order = Order.objects.get(pk=pk)
            serializer = OrderSerializer(order, data=request.data)
            if serializer.is_valid():
                serializer.save()
                logger.info(f"Order updated: {order.id} by {request.user.username}")
                notify_low_stock.delay()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        if request.user.role != 'admin':
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            order = Order.objects.get(pk=pk)
            order.delete()
            logger.info(f"Order deleted: {order.id} by {request.user.username}")
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

class InventoryListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    @method_decorator(cache_page(60*5))
    def get(self, request):
        if request.user.role not in ['admin', 'warehouse_manager']:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        inventories = Inventory.objects.all()
        warehouse_id = request.query_params.get('warehouse_id')
        if warehouse_id and warehouse_id.isdigit():
            inventories = inventories.filter(warehouse_id=warehouse_id)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(inventories, request)
        serializer = InventorySerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        if request.user.role not in ['admin', 'warehouse_manager']:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        serializer = InventorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            logger.info(f"Inventory created for product {serializer.data['product']} by {request.user.username}")
            notify_low_stock.delay()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class InventoryDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        if request.user.role not in ['admin', 'warehouse_manager']:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            inventory = Inventory.objects.get(pk=pk)
            serializer = InventorySerializer(inventory)
            return Response(serializer.data)
        except Inventory.DoesNotExist:
            return Response({"error": "Inventory not found"}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk):
        if request.user.role not in ['admin', 'warehouse_manager']:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            inventory = Inventory.objects.get(pk=pk)
            serializer = InventorySerializer(inventory, data=request.data)
            if serializer.is_valid():
                serializer.save()
                logger.info(f"Inventory updated: {inventory.id} by {request.user.username}")
                notify_low_stock.delay()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Inventory.DoesNotExist:
            return Response({"error": "Inventory not found"}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        if request.user.role != 'admin':
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            inventory = Inventory.objects.get(pk=pk)
            inventory.delete()
            logger.info(f"Inventory deleted: {inventory.id} by {request.user.username}")
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Inventory.DoesNotExist:
            return Response({"error": "Inventory not found"}, status=status.HTTP_404_NOT_FOUND)

class NotificationListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    @method_decorator(cache_page(60*5))
    def get(self, request):
        notifications = Notification.objects.filter(user=request.user)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(notifications, request)
        serializer = NotificationSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        if request.user.role not in ['admin', 'warehouse_manager']:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        serializer = NotificationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            logger.info(f"Notification created: {serializer.data['message']} by {request.user.username}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class StockBalanceCSVView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        task = export_stock_balance_to_csv.delay()
        return Response({"task_id": task.id}, status=status.HTTP_202_ACCEPTED)

class AuditLogView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        if request.user.role != 'admin':
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        logs = AuditLog.objects.all()
        if 'model_name' in request.query_params:
            logs = logs.filter(model_name=request.query_params['model_name'])
        if 'action' in request.query_params:
            logs = logs.filter(action=request.query_params['action'])
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(logs, request)
        serializer = AuditLogSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

class AnalyticsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role not in ['admin', 'analyst']:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        data = [{
            'total_products': Product.objects.count(),
            'total_warehouses': Warehouse.objects.count(),
            'low_stock_count': sum(
                1 for product in Product.objects.all()
                if (StockMovement.objects.filter(product=product, warehouse=product.warehouse).aggregate(
                    total=Sum(F('quantity') * Case(
                        When(operation='income', then=1),
                        When(operation='outcome', then=-1),
                        output_field=IntegerField()
                    ))
                )['total'] or 0) < product.min_stock
            ),
        }]
        return Response({'results': data})