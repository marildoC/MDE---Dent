from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


class CaseInsensitiveTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        username = attrs.get(self.username_field)
        if username:
            matching_user = (
                User.objects.filter(**{f"{self.username_field}__iexact": username})
                .order_by("id")
                .first()
            )
            if matching_user:
                attrs[self.username_field] = getattr(matching_user, self.username_field)

        return super().validate(attrs)


class CurrentUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
        )
        read_only_fields = fields
