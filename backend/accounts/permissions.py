from rest_framework.permissions import BasePermission

from .models import UserRole


class IsPatient(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.PATIENT
        )


class IsDentistStaff(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in {UserRole.DENTIST, UserRole.ADMIN}
        )


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.role == UserRole.ADMIN or request.user.is_superuser)
        )
