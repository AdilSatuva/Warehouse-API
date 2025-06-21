
from rest_framework import permissions

class HasRole(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        role = request.user.groups.first().name if request.user.groups.exists() else None
        if view.action in ['list', 'retrieve']:
            return role in ['admin', 'warehouse_manager', 'clerk', 'logistician', 'analyst', 'accountant']
        if view.action in ['create', 'update', 'destroy']:
            return role in ['admin', 'warehouse_manager', 'clerk', 'logistician']
        return False
