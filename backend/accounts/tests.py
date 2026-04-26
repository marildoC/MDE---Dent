from rest_framework.test import APIRequestFactory, APITestCase

from .models import User, UserRole
from .permissions import IsAdminRole, IsDentistStaff, IsPatient


class CurrentUserAPITests(APITestCase):
    def test_current_user_requires_authentication(self):
        response = self.client.get("/api/auth/me/")

        self.assertEqual(response.status_code, 401)

    def test_current_user_returns_authenticated_user_role(self):
        user = User.objects.create_user(
            username="patient1",
            password="testpass123",
            role=UserRole.PATIENT,
        )
        self.client.force_authenticate(user=user)

        response = self.client.get("/api/auth/me/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "patient1")
        self.assertEqual(response.data["role"], UserRole.PATIENT)


class RolePermissionTests(APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def _request_for(self, role, is_superuser=False):
        user = User(username=f"user-{role}", role=role, is_superuser=is_superuser)
        request = self.factory.get("/")
        request.user = user
        return request

    def test_patient_permission_allows_only_patient_role(self):
        permission = IsPatient()

        self.assertTrue(permission.has_permission(self._request_for(UserRole.PATIENT), None))
        self.assertFalse(permission.has_permission(self._request_for(UserRole.DENTIST), None))
        self.assertFalse(permission.has_permission(self._request_for(UserRole.ADMIN), None))

    def test_dentist_staff_permission_allows_dentist_and_admin(self):
        permission = IsDentistStaff()

        self.assertFalse(permission.has_permission(self._request_for(UserRole.PATIENT), None))
        self.assertTrue(permission.has_permission(self._request_for(UserRole.DENTIST), None))
        self.assertTrue(permission.has_permission(self._request_for(UserRole.ADMIN), None))

    def test_admin_permission_allows_admin_role_or_superuser(self):
        permission = IsAdminRole()

        self.assertFalse(permission.has_permission(self._request_for(UserRole.PATIENT), None))
        self.assertTrue(permission.has_permission(self._request_for(UserRole.ADMIN), None))
        self.assertTrue(
            permission.has_permission(
                self._request_for(UserRole.PATIENT, is_superuser=True),
                None,
            )
        )
