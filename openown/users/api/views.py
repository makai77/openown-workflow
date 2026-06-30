from typing import cast

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.mixins import UpdateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from openown.users.models import User

from .serializers import MeSerializer
from .serializers import UserSerializer


class LoginView(ObtainAuthToken):
    # Token login must not run SessionAuthentication. The default auth classes
    # (SessionAuthentication first; config/settings/base.py) authenticate any
    # Django session cookie the browser already holds — e.g. from logging into
    # /admin on the same origin — and then enforce CSRF. The token-less SPA login
    # POST carries no CSRF token, so that path 403s ("CSRF Failed"). Login needs no
    # prior authentication, so we clear the auth classes and ignore stray cookies.
    authentication_classes = ()


class UserViewSet(RetrieveModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    lookup_field = "pk"

    def get_queryset(self, *args, **kwargs):
        # IsAuthenticated gates this view, so request.user is always a real User;
        # narrow it here (drf-stubs types request.user as User | AnonymousUser).
        user = cast("User", self.request.user)
        return self.queryset.filter(id=user.id)

    @extend_schema(responses=MeSerializer)
    @action(detail=False)
    def me(self, request):
        serializer = MeSerializer(request.user, context={"request": request})
        return Response(status=status.HTTP_200_OK, data=serializer.data)
