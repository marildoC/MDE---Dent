from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    PATIENT = "PATIENT", "Patient"
    DENTIST = "DENTIST", "Dentist"
    ADMIN = "ADMIN", "Admin"


class User(AbstractUser):
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.PATIENT,
    )

    def __str__(self):
        return f"{self.username} ({self.role})"