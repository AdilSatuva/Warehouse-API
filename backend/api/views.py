"""
Views for the WarehouseAPI, providing RESTful endpoints for managing warehouse operations.
Includes functionality for products, warehouses, categories, stock movements, transfers, orders,
inventory, notifications, audit logs, and analytics.
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from django.db.models import Sum, F, Case, When, IntegerField, Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from django.views.decorators.cache import cache_page, never_cache
from django.utils.decorators import method_decorator
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.core.cache import cache
from django.views.decorators.vary import vary_on_cookie
from rest_framework.exceptions import ValidationError
from datetime import datetime
from django.utils import timezone
from warehouse.models import (
    Product, StockMovement, Warehouse, User, AuditLog, Category,
    Inventory, Notification, StockTransfer, Order, StockBalance
)
from api.serializers import (
    UserSerializer, AssignRoleSerializer, WarehouseSerializer, CategorySerializer,
    ProductSerializer, ProductCreateSerializer, StockMovementSerializer, StockBalanceSerializer,
    InventorySerializer, NotificationSerializer, AuditLogSerializer, StockTransferSerializer,
    OrderSerializer
)
from api.tasks import export_stock_balance_to_csv, notify_low_stock
from django_filters import rest_framework as filters

# Configure logger for the views module
logger = logging.getLogger(__name__)

class StandardResultsSetPagination(PageNumberPagination):
    """
    Custom pagination class for consistent API responses.
    Configures page size with a default of 10 and a maximum of 100.
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission allowing read-only access to authenticated users
    and write access to admins only.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            logger.debug(f"Read-only access granted for user: {request.user.username}")
            return request.user.is_authenticated
        is_admin = request.user.is_authenticated and request.user.role == 'admin'
        logger.info(f"Write access check for user: {request.user.username}, is_admin: {is_admin}")
        return is_admin

class CanManageProducts(permissions.BasePermission):
    """
    Custom permission for product management, allowing access to admins,
    warehouse managers, and clerks.
    """
    def has_permission(self, request, view):
        is_allowed = request.user.is_authenticated and request.user.role in ['admin', 'warehouse_manager', 'clerk']
        logger.info(f"Checking product management permission for user: {request.user.username}, "
                    f"role: {request.user.role}, authenticated: {request.user.is_authenticated}, allowed: {is_allowed}")
        return is_allowed

class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing products, supporting listing, retrieving, creating,
    updating, and deleting. Uses StockBalance for quantity calculations.
    """
    queryset = Product.objects.all().select_related('category', 'warehouse')
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]  # Removed SearchFilter
    filterset_fields = ['category', 'warehouse']
    ordering_fields = ['name', 'sku', 'total_quantity']
    ordering = ['name']

    def get_serializer_class(self):
        """
        Returns ProductCreateSerializer for creation and ProductSerializer otherwise.
        """
        if self.action == 'create':
            logger.debug("Using ProductCreateSerializer for product creation")
            return ProductCreateSerializer
        logger.debug("Using ProductSerializer for product operations")
        return ProductSerializer

    def get_queryset(self):
        """
        Customizes queryset with dynamic filtering and StockBalance annotation.
        """
        queryset = super().get_queryset().annotate(
            total_quantity=Sum('stock_balances__quantity')
        )
        category_id = self.request.query_params.get('category_id')
        warehouse_id = self.request.query_params.get('warehouse_id')
        if category_id:
            logger.info(f"Filtering products by category_id: {category_id}")
            queryset = queryset.filter(category_id=category_id)
        if warehouse_id:
            logger.info(f"Filtering products by warehouse_id: {warehouse_id}")
            queryset = queryset.filter(warehouse_id=warehouse_id)
        return queryset

    def perform_create(self, serializer):
        """
        Creates a product, logs the action, and sends a notification.
        """
        try:
            instance = serializer.save()
            logger.info(f"Product created: {instance.name} (SKU: {instance.sku}) by {self.request.user.username}")
            AuditLog.objects.create(
                user=self.request.user,
                action='create_product',
                model_name='Product',
                object_id=instance.id,
                details=f'Created product {instance.name} (SKU: {instance.sku})'
            )
            Notification.objects.create(
                user=self.request.user,
                message=f'Product {instance.name} added successfully',
                type='general'
            )
            notify_low_stock.delay()
        except ValidationError as e:
            logger.error(f"Validation error creating product: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Unexpected error creating product: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to create product'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_update(self, serializer):
        """
        Updates a product and logs the action.
        """
        try:
            instance = serializer.save()
            logger.info(f"Product updated: {instance.name} (SKU: {instance.sku}) by {self.request.user.username}")
            AuditLog.objects.create(
                user=self.request.user,
                action='update_product',
                model_name='Product',
                object_id=instance.id,
                details=f'Updated product {instance.name} (SKU: {instance.sku})'
            )
            notify_low_stock.delay()
        except Exception as e:
            logger.error(f"Error updating product: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to update product'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_destroy(self, instance):
        """
        Deletes a product and logs the action.
        """
        try:
            logger.info(f"Product deleted: {instance.name} (SKU: {instance.sku}) by {self.request.user.username}")
            AuditLog.objects.create(
                user=self.request.user,
                action='delete_product',
                model_name='Product',
                object_id=instance.id,
                details=f'Deleted product {instance.name} (SKU: {instance.sku})'
            )
            instance.delete()
        except Exception as e:
            logger.error(f"Error deleting product: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to delete product'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='low-stock')
    def low_stock(self, request):
        """
        Retrieves products with low stock (quantity <= min_stock).
        """
        try:
            warehouse_id = self.request.query_params.get('warehouse_id')
            queryset = Product.objects.filter(
                stock_balances__quantity__lte=F('min_stock')
            ).select_related('category', 'warehouse')
            if warehouse_id:
                logger.info(f"Filtering low stock products by warehouse_id: {warehouse_id}")
                queryset = queryset.filter(warehouse_id=warehouse_id)
            serializer = ProductSerializer(queryset, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error retrieving low stock products: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to retrieve low stock products'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class LoginView(TokenObtainPairView):
    """
    Handles user login, returning JWT tokens and role.
    """
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
    """
    Retrieves authenticated user's profile.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            serializer = UserSerializer(request.user)
            logger.info(f"User profile retrieved for: {request.user.username}")
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error retrieving user profile: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to retrieve profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserListCreateView(APIView):
    """
    Lists all users or creates a new user (admin only).
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role != 'admin':
            logger.warning(f"User {request.user.username} attempted to list users without admin role")
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            users = User.objects.all()
            paginator = StandardResultsSetPagination()
            page = paginator.paginate_queryset(users, request)
            serializer = UserSerializer(page, many=True)
            logger.info(f"User list retrieved by: {request.user.username}")
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            logger.error(f"Error retrieving user list: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to retrieve users'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        if request.user.role != 'admin':
            logger.warning(f"User {request.user.username} attempted to create user without admin role")
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            serializer = UserSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                logger.info(f"User created: {serializer.data['username']} by {request.user.username}")
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to create user'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserAssignRoleView(APIView):
    """
    Assigns roles to users (admin only).
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if request.user.role != 'admin':
            logger.warning(f"User {request.user.username} attempted to assign role without admin role")
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
            logger.error(f"User not found for role assignment: pk={pk}")
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error assigning role: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to assign role'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WarehouseListCreateView(APIView):
    """
    Lists warehouses or creates a new one.
    Supports search by name or location.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            logger.info(f"Warehouse list requested by {request.user.username}")
            warehouses = Warehouse.objects.all()
            search = request.query_params.get('search')
            if search:
                logger.info(f"Searching warehouses with query: {search}")
                warehouses = warehouses.filter(Q(name__icontains=search) | Q(location__icontains=search))
            paginator = StandardResultsSetPagination()
            page = paginator.paginate_queryset(warehouses, request)
            serializer = WarehouseSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            logger.error(f"Error retrieving warehouse list: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to retrieve warehouses'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @method_decorator(never_cache)
    def post(self, request):
        if request.user.role not in ['admin', 'warehouse_manager']:
            logger.warning(f"User {request.user.username} attempted to create warehouse without permission")
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            serializer = WarehouseSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(created_by=request.user)
                logger.info(f"Warehouse created: {serializer.data['name']} by {request.user.username}")
                cache.delete_pattern('warehouse_list*')
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            logger.error(f"Warehouse creation failed: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating warehouse: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to create warehouse'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WarehouseDetailView(APIView):
    """
    Retrieves, updates, or deletes a specific warehouse.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            warehouse = Warehouse.objects.get(pk=pk)
            serializer = WarehouseSerializer(warehouse)
            logger.info(f"Warehouse retrieved: {warehouse.name} by {request.user.username}")
            return Response(serializer.data)
        except Warehouse.DoesNotExist:
            logger.error(f"Warehouse not found: pk={pk}")
            return Response({"error": "Warehouse not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error retrieving warehouse: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to retrieve warehouse'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @method_decorator(never_cache)
    def put(self, request, pk):
        if request.user.role != 'admin':
            logger.warning(f"User {request.user.username} attempted to update warehouse without admin role")
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
            logger.error(f"Warehouse not found for update: pk={pk}")
            return Response({"error": "Warehouse not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error updating warehouse: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to update warehouse'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @method_decorator(never_cache)
    def delete(self, request, pk):
        if request.user.role != 'admin':
            logger.warning(f"User {request.user.username} attempted to delete warehouse without admin role")
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            warehouse = Warehouse.objects.get(pk=pk)
            warehouse.delete()
            logger.info(f"Warehouse deleted: {warehouse.name} by {request.user.username}")
            cache.delete_pattern('warehouse_list*')
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Warehouse.DoesNotExist:
            logger.error(f"Warehouse not found for deletion: pk={pk}")
            return Response({"error": "Warehouse not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error deleting warehouse: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to delete warehouse'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WarehouseProductsView(APIView):
    """
    Lists products in a specific warehouse.
    """
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
            logger.info(f"Products retrieved for warehouse {warehouse.name} by {request.user.username}")
            return paginator.get_paginated_response(serializer.data)
        except Warehouse.DoesNotExist:
            logger.error(f"Warehouse not found: pk={pk}")
            return Response({"error": "Warehouse not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error retrieving warehouse products: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to retrieve products'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CategoryListCreateView(APIView):
    """
    Lists categories or creates a new one.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @method_decorator(cache_page(60*10))
    def get(self, request):
        try:
            categories = Category.objects.all()
            paginator = StandardResultsSetPagination()
            page = paginator.paginate_queryset(categories, request)
            serializer = CategorySerializer(page, many=True)
            logger.info(f"Category list retrieved by: {request.user.username}")
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            logger.error(f"Error retrieving category list: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to retrieve categories'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @method_decorator(never_cache)
    def post(self, request):
        if request.user.role not in ['admin', 'warehouse_manager']:
            logger.warning(f"User {request.user.username} attempted to create category without permission")
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            serializer = CategorySerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(created_by=request.user)
                logger.info(f"Category created: {serializer.data['name']} by {request.user.username}")
                cache.delete_pattern('category_list*')
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating category: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to create category'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CategoryDetailView(APIView):
    """
    Retrieves, updates, or deletes a specific category.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            category = Category.objects.get(pk=pk)
            serializer = CategorySerializer(category)
            logger.info(f"Category retrieved: {category.name} by {request.user.username}")
            return Response(serializer.data)
        except Category.DoesNotExist:
            logger.error(f"Category not found: pk={pk}")
            return Response({"error": "Category not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error retrieving category: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to retrieve category'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @method_decorator(never_cache)
    def put(self, request, pk):
        if request.user.role not in ['admin', 'warehouse_manager']:
            logger.warning(f"User {request.user.username} attempted to update category without permission")
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
            logger.error(f"Category not found for update: pk={pk}")
            return Response({"error": "Category not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error updating category: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to update category'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @method_decorator(never_cache)
    def delete(self, request, pk):
        if request.user.role != 'admin':
            logger.warning(f"User {request.user.username} attempted to delete category without admin role")
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            category = Category.objects.get(pk=pk)
            category.delete()
            logger.info(f"Category deleted: {category.name} by {request.user.username}")
            cache.delete_pattern('category_list*')
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Category.DoesNotExist:
            logger.error(f"Category not found for deletion: pk={pk}")
            return Response({"error": "Category not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error deleting category: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to delete category'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StockIncomeOutcomeView(APIView):
    """
    Creates stock movement records (in/out) and updates StockBalance.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated, CanManageProducts]

    @method_decorator(never_cache)
    def post(self, request):
        if request.user.role not in ['admin', 'warehouse_manager', 'clerk']:
            logger.warning(f"User {request.user.username} attempted stock operation without permission")
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            data = request.data.copy()
            data['created_by'] = request.user.id
            serializer = StockMovementSerializer(data=data)
            if serializer.is_valid():
                product = Product.objects.get(id=data['product'])
                warehouse = Warehouse.objects.get(id=data['warehouse'])
                if data['operation'] == 'out':
                    balance = StockBalance.objects.filter(product=product, warehouse=warehouse).aggregate(
                        total=Sum('quantity')
                    )['total'] or 0
                    if balance < data['quantity']:
                        logger.error(f"Insufficient stock for product {product.name} in warehouse {warehouse.name}")
                        return Response({"error": "Insufficient stock"}, status=status.HTTP_400_BAD_REQUEST)
                serializer.save()
                # Update StockBalance
                stock_balance, created = StockBalance.objects.get_or_create(
                    product=product,
                    warehouse=warehouse,
                    defaults={'quantity': 0}
                )
                if data['operation'] == 'in':
                    stock_balance.quantity += data['quantity']
                elif data['operation'] == 'out':
                    stock_balance.quantity -= data['quantity']
                stock_balance.save()
                logger.info(f"Stock {data['operation']}: {product.name} ({data['quantity']}) by {request.user.username}")
                cache.delete_pattern('stock_movements*')
                cache.delete_pattern('stock_balance*')
                notify_low_stock.delay()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Product.DoesNotExist:
            logger.error(f"Product not found: id={data.get('product')}")
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
        except Warehouse.DoesNotExist:
            logger.error(f"Warehouse not found: id={data.get('warehouse')}")
            return Response({"error": "Warehouse not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in stock operation: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to process stock operation'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StockMovementsView(APIView):
    """
    Lists stock movement records with filtering and pagination.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['product', 'warehouse', 'operation', 'created_at']
    pagination_class = StandardResultsSetPagination

    @method_decorator(cache_page(60*5))
    def get(self, request, product_id=None):
        try:
            movements = StockMovement.objects.all()
            if product_id:
                movements = movements.filter(product_id=product_id)
            warehouse_id = request.query_params.get('warehouse_id')
            if warehouse_id and warehouse_id.isdigit():
                movements = movements.filter(warehouse_id=warehouse_id)
            if 'operation' in request.query_params:
                movements = movements.filter(operation=request.query_params['operation'])
            if 'date_start' in request.query_params:
                date_start_str = request.query_params.get('date_start')
                if date_start_str:
                    try:
                        date_start = datetime.strptime(date_start_str, '%Y-%m-%d %H:%M:%S')
                        date_start = timezone.make_aware(date_start)
                        movements = movements.filter(created_at__gte=date_start)
                    except ValueError:
                        logger.warning(f"Invalid date_start format: {date_start_str}")
                        return Response(
                            {"error": "Invalid date_start format. Use YYYY-MM-DD HH:MM:SS"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
            if 'date_end' in request.query_params:
                date_end_str = request.query_params.get('date_end')
                if date_end_str:
                    try:
                        date_end = datetime.strptime(date_end_str, '%Y-%m-%d %H:%M:%S')
                        date_end = timezone.make_aware(date_end)
                        movements = movements.filter(created_at__lte=date_end)
                    except ValueError:
                        logger.warning(f"Invalid date_end format: {date_end_str}")
                        return Response(
                            {"error": "Invalid date_end format. Use YYYY-MM-DD HH:MM:SS"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(movements, request)
            serializer = StockMovementSerializer(page, many=True)
            logger.info(f"Stock movements retrieved by: {request.user.username}")
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            logger.error(f"Error in StockMovementsView: {str(e)}", exc_info=True)
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StockBalanceView(APIView):
    """
    Lists current stock balances using StockBalance model.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    @method_decorator(cache_page(60*5))
    def get(self, request, product_id=None):
        try:
            balances = StockBalance.objects.select_related('product', 'warehouse')
            if product_id:
                balances = balances.filter(product_id=product_id)
            warehouse_id = request.query_params.get('warehouse_id')
            if warehouse_id and warehouse_id.isdigit():
                balances = balances.filter(warehouse_id=warehouse_id)
            balances = balances.values(
                'product', 'product__name', 'warehouse__name'
            ).annotate(
                total_quantity=Sum('quantity')
            )
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(balances, request)
            serializer = StockBalanceSerializer(page, many=True)
            logger.info(f"Stock balances retrieved by: {request.user.username}")
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            logger.error(f"Error retrieving stock balances: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to retrieve stock balances'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class LowStockView(APIView):
    """
    Lists products with low stock based on StockBalance.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    @method_decorator(cache_page(60*5))
    def get(self, request):
        try:
            products = Product.objects.select_related('warehouse').all()
            warehouse_id = request.query_params.get('warehouse_id')
            if warehouse_id and warehouse_id.isdigit():
                products = products.filter(warehouse_id=warehouse_id)
            low_stock_products = []
            for product in products:
                try:
                    if not product.warehouse:
                        logger.warning(f"Product {product.name} has no warehouse assigned")
                        continue
                    balance = StockBalance.objects.filter(product=product, warehouse=product.warehouse).aggregate(
                        total=Sum('quantity')
                    )['total'] or 0
                    if balance < product.min_stock:
                        low_stock_products.append({
                            'id': product.id,
                            'name': product.name,
                            'sku': product.sku,
                            'current_stock': balance,
                            'min_stock': product.min_stock,
                            'warehouse_name': product.warehouse.name
                        })
                except Exception as e:
                    logger.error(f"Error processing product {product.id}: {str(e)}")
                    continue
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(low_stock_products, request)
            serializer = StockBalanceSerializer(page, many=True)
            logger.info(f"Low stock products retrieved by: {request.user.username}")
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            logger.error(f"LowStockView error: {str(e)}", exc_info=True)
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StockTransferListCreateView(APIView):
    """
    Lists or creates stock transfers between warehouses.
    Updates StockBalance accordingly.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role not in ['admin', 'warehouse_manager', 'logistician']:
            logger.warning(f"User {request.user.username} attempted to list transfers without permission")
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            transfers = StockTransfer.objects.all()
            paginator = StandardResultsSetPagination()
            page = paginator.paginate_queryset(transfers, request)
            serializer = StockTransferSerializer(page, many=True)
            logger.info(f"Stock transfers retrieved by: {request.user.username}")
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            logger.error(f"Error retrieving stock transfers: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to retrieve transfers'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        if request.user.role not in ['admin', 'warehouse_manager', 'logistician']:
            logger.warning(f"User {request.user.username} attempted to create transfer without permission")
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            serializer = StockTransferSerializer(data=request.data)
            if serializer.is_valid():
                product = Product.objects.get(id=request.data['product'])
                from_warehouse = Warehouse.objects.get(id=request.data['from_warehouse'])
                balance = StockBalance.objects.filter(product=product, warehouse=from_warehouse).aggregate(
                    total=Sum('quantity')
                )['total'] or 0
                if balance < request.data['quantity']:
                    logger.error(f"Insufficient stock for transfer of {product.name} from {from_warehouse.name}")
                    return Response({"error": "Insufficient stock in source warehouse"}, status=status.HTTP_400_BAD_REQUEST)
                serializer.save(created_by=request.user)
                # Update StockBalance
                from_balance, _ = StockBalance.objects.get_or_create(
                    product=product,
                    warehouse=from_warehouse,
                    defaults={'quantity': 0}
                )
                to_balance, _ = StockBalance.objects.get_or_create(
                    product=product,
                    warehouse=serializer.validated_data['to_warehouse'],
                    defaults={'quantity': 0}
                )
                from_balance.quantity -= request.data['quantity']
                to_balance.quantity += request.data['quantity']
                from_balance.save()
                to_balance.save()
                logger.info(f"Transfer created: {product.name} ({request.data['quantity']}) from {from_warehouse.name} "
                            f"to {serializer.validated_data['to_warehouse'].name} by {request.user.username}")
                cache.delete_pattern('stock_balance*')
                notify_low_stock.delay()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Product.DoesNotExist:
            logger.error(f"Product not found: id={request.data.get('product')}")
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
        except Warehouse.DoesNotExist:
            logger.error(f"Warehouse not found: id={request.data.get('from_warehouse')}")
            return Response({"error": "Warehouse not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error creating stock transfer: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to create transfer'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StockTransferDetailView(APIView):
    """
    Retrieves, updates, or deletes a specific stock transfer.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        if request.user.role not in ['admin', 'warehouse_manager', 'logistician']:
            logger.warning(f"User {request.user.username} attempted to retrieve transfer without permission")
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            transfer = StockTransfer.objects.get(pk=pk)
            serializer = StockTransferSerializer(transfer)
            logger.info(f"Stock transfer {pk} retrieved by: {request.user.username}")
            return Response(serializer.data)
        except StockTransfer.DoesNotExist:
            logger.error(f"Stock transfer not found: pk={pk}")
            return Response({"error": "Transfer not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error retrieving stock transfer: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to retrieve transfer'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, pk):
        if request.user.role not in ['admin', 'warehouse_manager', 'logistician']:
            logger.warning(f"User {request.user.username} attempted to update transfer without permission")
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            transfer = StockTransfer.objects.get(pk=pk)
            serializer = StockTransferSerializer(transfer, data=request.data)
            if serializer.is_valid():
                serializer.save()
                logger.info(f"Transfer updated: {transfer.id} by {request.user.username}")
                cache.delete_pattern('stock_balance*')
                notify_low_stock.delay()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except StockTransfer.DoesNotExist:
            logger.error(f"Stock transfer not found for update: pk={pk}")
            return Response({"error": "Transfer not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error updating stock transfer: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to update transfer'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, pk):
        if request.user.role != 'admin':
            logger.warning(f"User {request.user.username} attempted to delete transfer without admin role")
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            transfer = StockTransfer.objects.get(pk=pk)
            transfer.delete()
            logger.info(f"Transfer deleted: {transfer.id} by {request.user.username}")
            cache.delete_pattern('stock_balance*')
            return Response(status=status.HTTP_204_NO_CONTENT)
        except StockTransfer.DoesNotExist:
            logger.error(f"Stock transfer not found for deletion: pk={pk}")
            return Response({"error": "Transfer not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error deleting stock transfer: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to delete transfer'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class OrderListCreateView(APIView):
    """
    Lists or creates orders.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role not in ['admin', 'warehouse_manager', 'logistician']:
            logger.warning(f"User {request.user.username} attempted to list orders without permission")
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            orders = Order.objects.all()
            paginator = StandardResultsSetPagination()
            page = paginator.paginate_queryset(orders, request)
            serializer = OrderSerializer(page, many=True)
            logger.info(f"Orders retrieved by: {request.user.username}")
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            logger.error(f"Error retrieving orders: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to retrieve orders'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        if request.user.role not in ['admin', 'warehouse_manager', 'logistician']:
            logger.warning(f"User {request.user.username} attempted to create order without permission")
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            serializer = OrderSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(created_by=request.user)
                logger.info(f"Order created: {serializer.data['id']} by {request.user.username}")
                notify_low_stock.delay()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating order: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to create order'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class OrderDetailView(APIView):
    """
    Retrieves, updates, or deletes a specific order.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        if request.user.role not in ['admin', 'warehouse_manager', 'logistician']:
            logger.warning(f"User {request.user.username} attempted to retrieve order without permission")
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            order = Order.objects.get(pk=pk)
            serializer = OrderSerializer(order)
            logger.info(f"Order {pk} retrieved by: {request.user.username}")
            return Response(serializer.data)
        except Order.DoesNotExist:
            logger.error(f"Order not found: pk={pk}")
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error retrieving order: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to retrieve order'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, pk):
        if request.user.role not in ['admin', 'warehouse_manager', 'logistician']:
            logger.warning(f"User {request.user.username} attempted to update order without permission")
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
            logger.error(f"Order not found for update: pk={pk}")
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error updating order: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to update order'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, pk):
        if request.user.role != 'admin':
            logger.warning(f"User {request.user.username} attempted to delete order without admin role")
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            order = Order.objects.get(pk=pk)
            order.delete()
            logger.info(f"Order deleted: {order.id} by {request.user.username}")
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Order.DoesNotExist:
            logger.error(f"Order not found for deletion: pk={pk}")
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error deleting order: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to delete order'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class InventoryListCreateView(APIView):
    """
    Lists or creates inventory records.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    @method_decorator(cache_page(60*5))
    def get(self, request):
        if request.user.role not in ['admin', 'warehouse_manager']:
            logger.warning(f"User {request.user.username} attempted to list inventory without permission")
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            inventories = Inventory.objects.all()
            warehouse_id = request.query_params.get('warehouse_id')
            if warehouse_id and warehouse_id.isdigit():
                inventories = inventories.filter(warehouse_id=warehouse_id)
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(inventories, request)
            serializer = InventorySerializer(page, many=True)
            logger.info(f"Inventory retrieved by: {request.user.username}")
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            logger.error(f"Error retrieving inventory: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to retrieve inventory'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        if request.user.role not in ['admin', 'warehouse_manager']:
            logger.warning(f"User {request.user.username} attempted to create inventory without permission")
            return Response({"error": "Permission denied"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            serializer = InventorySerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(created_by=request.user)
                logger.info(f"Inventory created for product {request.data.get('product')} by {request.user.username}")
                notify_low_stock.delay()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating inventory: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to create inventory'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class InventoryDetailView(APIView):
    """
    Retrieves, updates, or deletes a specific inventory record.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        if request.user.role not in ['admin', 'warehouse_manager']:
            logger.warning(f"User {request.user.username} attempted to retrieve inventory without permission")
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            inventory = Inventory.objects.get(pk=pk)
            serializer = InventorySerializer(inventory)
            logger.info(f"Inventory {pk} retrieved by: {request.user.username}")
            return Response(serializer.data)
        except Inventory.DoesNotExist:
            logger.error(f"Inventory not found: pk={pk}")
            return Response({"error": "Inventory not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error retrieving inventory: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to retrieve inventory'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, pk):
        if request.user.role not in ['admin', 'warehouse_manager']:
            logger.warning(f"User {request.user.username} attempted to update inventory without permission")
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
            logger.error(f"Inventory not found for update: pk={pk}")
            return Response({"error": "Inventory not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error updating inventory: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to update inventory'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, pk):
        if request.user.role != 'admin':
            logger.warning(f"User {request.user.username} attempted to delete inventory without admin role")
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            inventory = Inventory.objects.get(pk=pk)
            inventory.delete()
            logger.info(f"Inventory deleted: {inventory.id} by {request.user.username}")
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Inventory.DoesNotExist:
            logger.error(f"Inventory not found for deletion: pk={pk}")
            return Response({"error": "Inventory not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error deleting inventory: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to delete inventory'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class NotificationListCreateView(APIView):
    """
    Lists notifications for the authenticated user or creates a new one.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    @method_decorator(cache_page(60*5))
    def get(self, request):
        try:
            notifications = Notification.objects.filter(user=request.user)
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(notifications, request)
            serializer = NotificationSerializer(page, many=True)
            logger.info(f"Notifications retrieved by: {request.user.username}")
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            logger.error(f"Error retrieving notifications: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to retrieve notifications'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        if request.user.role not in ['admin', 'warehouse_manager']:
            logger.warning(f"User {request.user.username} attempted to create notification without permission")
            return Response({"error": "Permission denied"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            serializer = NotificationSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(user=request.user)
                logger.info(f"Notification created: {serializer.data['message']} by {request.user.username}")
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating notification: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to create notification'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StockBalanceCsvView(APIView):
    """
    Triggers a CSV export of stock balances.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            task = export_stock_balance_to_csv.delay()
            logger.info(f"Stock balance CSV export triggered by: {request.user.username}")
            return Response({"task_id": task.id}, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            logger.error(f"Error triggering stock balance CSV export: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to trigger CSV export'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AuditLogView(APIView):
    """
    Lists audit logs (admin only).
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        if request.user.role != 'admin':
            logger.warning(f"User {request.user.username} attempted to list audit logs without admin role")
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            logs = AuditLog.objects.all()
            if 'model_name' in request.query_params:
                logs = logs.filter(model_name=request.query_params['model_name'])
            if 'action' in request.query_params:
                logs = logs.filter(action=request.query_params['action'])
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(logs, request)
            serializer = AuditLogSerializer(page, many=True)
            logger.info(f"Audit logs retrieved by: {request.user.username}")
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            logger.error(f"Error retrieving audit logs: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to retrieve audit logs'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AnalyticsView(APIView):
    """
    Provides warehouse analytics (admin or analyst only).
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role not in ['admin', 'analyst']:
            logger.warning(f"User {request.user.username} attempted to access analytics without permission")
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            data = [{
                'total_products': Product.objects.count(),
                'total_warehouses': Warehouse.objects.count(),
                'low_stock_count': sum(
                    1 for product in Product.objects.all()
                    if (StockBalance.objects.filter(product=product, warehouse=product.warehouse).aggregate(
                        total=Sum('quantity')
                    )['total'] or 0) < product.min_stock
                ),
            }]
            logger.info(f"Analytics retrieved by: {request.user.username}")
            return Response({'results': data})
        except Exception as e:
            logger.error(f"Error retrieving analytics: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to retrieve analytics'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)