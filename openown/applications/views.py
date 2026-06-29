from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

from rest_framework import mixins
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Application
from .models import ApplicationQuerySet
from .permissions import IsApplicant
from .permissions import IsReviewer
from .serializers import ApplicationCreateSerializer
from .serializers import ApplicationDetailSerializer
from .serializers import ApplicationListSerializer
from .serializers import ApplicationUpdateSerializer
from .serializers import TransitionCommentSerializer
from .services import approve_application
from .services import reject_application
from .services import return_application
from .services import start_review_application
from .services import submit_application
from .services.exceptions import WorkflowError

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.serializers import BaseSerializer

    from openown.users.models import User


def _actor(request: Request) -> User:
    # The permission classes (IsApplicant / IsReviewer) guarantee an authenticated
    # User with a role by the time an action runs, but drf-stubs types request.user
    # as User | AnonymousUser. Narrow it here, at the HTTP boundary, so the service
    # layer can demand a real User.
    return cast("User", request.user)


def workflow_error_response(exc: WorkflowError) -> Response:
    return Response(
        {"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
        status=exc.status_code,
    )


def _detail_queryset() -> ApplicationQuerySet:
    # Single source of truth for the "fully-loaded for detail" read shape, so every
    # transition response returns the object with owner + trail already resolved
    # instead of lazy-loading them in the serializer (Playbook §6.6).
    return Application.objects.with_owner().with_audit_trail()


class ApplicationViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    # Deliberately not a full ModelViewSet: destroy is omitted. The endpoint
    # contract has no DELETE, and removing an application would erase its audit
    # trail — the opposite of an auditable workflow.
    permission_classes = [IsApplicant]

    def get_queryset(self) -> ApplicationQuerySet:
        base = Application.objects.for_applicant(_actor(self.request))
        # Cheap list path vs. fully-loaded detail path — never carry the audit
        # trail prefetch into a list response that won't render it.
        if self.action == "list":
            return base.with_owner()
        return base.with_owner().with_audit_trail()

    def get_serializer_class(self) -> type[BaseSerializer]:
        if self.action == "create":
            return ApplicationCreateSerializer
        if self.action in {"update", "partial_update"}:
            return ApplicationUpdateSerializer
        if self.action == "list":
            return ApplicationListSerializer
        return ApplicationDetailSerializer

    def perform_create(self, serializer: BaseSerializer) -> None:
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["post"])
    def submit(self, request: Request, pk: int | None = None) -> Response:
        application = self.get_object()
        try:
            application = submit_application(
                application=application,
                actor=_actor(request),
            )
        except WorkflowError as exc:
            return workflow_error_response(exc)
        # Re-read through the detail queryset so the response carries the new audit
        # row without a per-row lazy load.
        application = _detail_queryset().get(pk=application.pk)
        return Response(ApplicationDetailSerializer(application).data)


class ReviewerApplicationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsReviewer]

    def get_queryset(self) -> ApplicationQuerySet:
        base = Application.objects.for_reviewer_queue()
        status_param = self.request.query_params.get("status")
        if status_param:
            base = base.filter(status=status_param)
        if self.action == "list":
            return base.with_owner()
        return base.with_owner().with_audit_trail()

    def get_serializer_class(self) -> type[BaseSerializer]:
        if self.action == "list":
            return ApplicationListSerializer
        return ApplicationDetailSerializer

    def _transition_response(self, application: Application) -> Response:
        application = _detail_queryset().get(pk=application.pk)
        return Response(ApplicationDetailSerializer(application).data)

    @action(detail=True, methods=["post"], url_path="start-review")
    def start_review(self, request: Request, pk: int | None = None) -> Response:
        application = self.get_object()
        try:
            application = start_review_application(
                application=application,
                actor=_actor(request),
            )
        except WorkflowError as exc:
            return workflow_error_response(exc)
        return self._transition_response(application)

    @action(detail=True, methods=["post"])
    def approve(self, request: Request, pk: int | None = None) -> Response:
        application = self.get_object()
        try:
            application = approve_application(
                application=application,
                actor=_actor(request),
            )
        except WorkflowError as exc:
            return workflow_error_response(exc)
        return self._transition_response(application)

    @action(detail=True, methods=["post"])
    def reject(self, request: Request, pk: int | None = None) -> Response:
        serializer = TransitionCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = self.get_object()
        try:
            application = reject_application(
                application=application,
                actor=_actor(request),
                comment=serializer.validated_data["comment"],
            )
        except WorkflowError as exc:
            return workflow_error_response(exc)
        return self._transition_response(application)

    @action(detail=True, methods=["post"], url_path="return")
    def return_for_changes(self, request: Request, pk: int | None = None) -> Response:
        serializer = TransitionCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = self.get_object()
        try:
            application = return_application(
                application=application,
                actor=_actor(request),
                comment=serializer.validated_data["comment"],
            )
        except WorkflowError as exc:
            return workflow_error_response(exc)
        return self._transition_response(application)
