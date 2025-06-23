import logging
from rest_framework import permissions

logger = logging.getLogger(__name__)

class HasRole(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            logger.debug(f"User is not authenticated: {request.user}")
            return False
        
        if request.user.is_superuser:
            logger.debug(f"User {request.user.username} is superuser, granting access")
            return True
        
        role = request.user.role
        action = view.action
        logger.debug(f"Checking permission for user: {request.user.username}, role: {role}, action: {action}")

        if action in ['list', 'retrieve']:
            allowed = role in ['admin', 'warehouse_manager', 'clerk', 'logistician', 'analyst']
            logger.debug(f"Read action ({action}), allowed: {allowed}")
            return allowed
        
        if action in ['create', 'update', 'partial_update', 'destroy']:
            allowed = role in ['admin', 'warehouse_manager', 'clerk', 'logistician']
            logger.debug(f"Write action ({action}), allowed: {allowed}")
            return allowed
        
        logger.warning(f"Unknown action: {action} for user {request.user.username}, role: {role}, access denied")
        return False

    # Пример проверки на уровне объекта (раскомментируйте, если нужна)
    # def has_object_permission(self, request, view, obj):
    #     # Например, проверка, что товар принадлежит складу пользователя
    #     if hasattr(obj, 'warehouse') and hasattr(request.user, 'warehouse_id'):
    #         allowed = obj.warehouse_id == request.user.warehouse_id
    #         logger.debug(f"Object permission check: user {request.user.username}, object warehouse_id: {obj.warehouse_id}, user warehouse_id: {request.user.warehouse_id}, allowed: {allowed}")
    #         return allowed
    #     return True  # Разрешать по умолчанию, если нет ограничений