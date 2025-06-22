from rest_framework import permissions

class HasRole(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = request.user.role
        if view.action in ['list', 'retrieve']:
            return role in ['admin', 'warehouse_manager', 'clerk', 'logistician', 'analyst']
        if view.action in ['create', 'update', 'partial_update', 'destroy']:
            return role in ['admin', 'warehouse_manager', 'clerk', 'logistician']
        return False