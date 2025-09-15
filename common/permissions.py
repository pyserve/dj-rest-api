from rest_framework import permissions
from rest_framework.permissions import BasePermission

action_permission_map = {
    "GET": "view",
    "POST": "add",
    "PUT": "change",
    "DELETE": "delete",
}


class GroupPermission(BasePermission):
    def has_permission(self, request, view):

        action_permission = action_permission_map.get(request.method)
        model_name = view.queryset.model.__name__
        if action_permission:
            perm_codename = f"{action_permission}_{model_name.lower()}"
            user_groups = request.user.groups.all()
            for group in user_groups:
                if group.permissions.filter(codename=perm_codename).exists():
                    return True
        return False


class RolePermission(BasePermission):
    def has_permission(self, request, view):
        action_permission = action_permission_map.get(request.method)
        model_name = view.queryset.model.__name__
        if action_permission:
            perm_codename = f"{action_permission}_{model_name.lower()}"
            user_roles = request.user.roles.all()
            for role in user_roles:
                if role.permissions.filter(codename=perm_codename).exists():
                    return True
        return False


class GroupRolePermission(BasePermission):
    def has_permission(self, request, view):
        group_permission = GroupPermission()
        role_permission = RolePermission()

        if group_permission.has_permission(request, view):
            return True

        if role_permission.has_permission(request, view):
            return True

        return False


class IsOwnerReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if obj.owner != request.user:
            return False
        return request.method in permissions.SAFE_METHODS


class BaseAccessPermission(BasePermission):
    def __init__(self):
        self.group_role_perm = GroupRolePermission()
        self.owner_perm = IsOwnerReadOnly()
        super().__init__()

    def has_permission(self, request, view):
        return self.group_role_perm.has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        return self.group_role_perm.has_permission(
            request, view
        ) or self.owner_perm.has_object_permission(request, view, obj)
