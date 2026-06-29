from rest_framework import serializers

from openown.users.models import User


class UserSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ["name", "url"]

        extra_kwargs = {
            "url": {"view_name": "api:user-detail", "lookup_field": "pk"},
        }


class MeSerializer(serializers.ModelSerializer[User]):
    """The authenticated user's own identity + role.

    Used only by ``UserViewSet.me`` so the SPA can route by role (applicant vs
    reviewer) after login. Read-only; the CRUD contract for ``/api/users/{pk}/``
    stays on ``UserSerializer``.
    """

    class Meta:
        model = User
        fields = ["id", "email", "name", "role"]
        read_only_fields = fields
