from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Application
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


def workflow_error_response(exc: WorkflowError) -> Response:
    return Response(
        {"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
        status=exc.status_code,
    )


def _detail_queryset():
    # Single source of truth for the "fully-loaded for detail" read shape, so every
    # transition response returns the object with owner + trail already resolved
    # instead of lazy-loading them in the serializer (Playbook §6.6).
    return Application.objects.with_owner().with_audit_trail()


class ApplicationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsApplicant]

    def get_queryset(self):
        base = Application.objects.for_applicant(self.request.user)
        # Cheap list path vs. fully-loaded detail path — never carry the audit
        # trail prefetch into a list response that won't render it.
        if self.action == "list":
            return base.with_owner()
        return base.with_owner().with_audit_trail()

    def get_serializer_class(self):
        if self.action == "create":
            return ApplicationCreateSerializer
        if self.action in {"update", "partial_update"}:
            return ApplicationUpdateSerializer
        if self.action == "list":
            return ApplicationListSerializer
        return ApplicationDetailSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        application = self.get_object()
        try:
            application = submit_application(
                application=application,
                actor=request.user,
            )
        except WorkflowError as exc:
            return workflow_error_response(exc)
        # Re-read through the detail queryset so the response carries the new audit
        # row without a per-row lazy load.
        application = _detail_queryset().get(pk=application.pk)
        return Response(ApplicationDetailSerializer(application).data)


class ReviewerApplicationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsReviewer]

    def get_queryset(self):
        base = Application.objects.for_reviewer_queue()
        status_param = self.request.query_params.get("status")
        if status_param:
            base = base.filter(status=status_param)
        if self.action == "list":
            return base.with_owner()
        return base.with_owner().with_audit_trail()

    def get_serializer_class(self):
        if self.action == "list":
            return ApplicationListSerializer
        return ApplicationDetailSerializer

    def _transition_response(self, application):
        application = _detail_queryset().get(pk=application.pk)
        return Response(ApplicationDetailSerializer(application).data)

    @action(detail=True, methods=["post"], url_path="start-review")
    def start_review(self, request, pk=None):
        application = self.get_object()
        try:
            application = start_review_application(
                application=application,
                actor=request.user,
            )
        except WorkflowError as exc:
            return workflow_error_response(exc)
        return self._transition_response(application)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        application = self.get_object()
        try:
            application = approve_application(
                application=application,
                actor=request.user,
            )
        except WorkflowError as exc:
            return workflow_error_response(exc)
        return self._transition_response(application)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        serializer = TransitionCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = self.get_object()
        try:
            application = reject_application(
                application=application,
                actor=request.user,
                comment=serializer.validated_data["comment"],
            )
        except WorkflowError as exc:
            return workflow_error_response(exc)
        return self._transition_response(application)

    @action(detail=True, methods=["post"], url_path="return")
    def return_for_changes(self, request, pk=None):
        serializer = TransitionCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = self.get_object()
        try:
            application = return_application(
                application=application,
                actor=request.user,
                comment=serializer.validated_data["comment"],
            )
        except WorkflowError as exc:
            return workflow_error_response(exc)
        return self._transition_response(application)
