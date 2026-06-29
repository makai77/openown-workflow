from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

from drf_spectacular.utils import OpenApiExample
from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.utils import extend_schema
from drf_spectacular.utils import extend_schema_view
from rest_framework import mixins
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Application
from .models import ApplicationQuerySet
from .permissions import IsApplicant
from .permissions import IsReviewer
from .schema import ErrorResponseSerializer
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


# --- OpenAPI documentation (drf-spectacular) ------------------------------------
# These describe the transition actions only; standard CRUD is auto-documented.
# Every error code/message below is copied verbatim from services/exceptions.py and
# services/workflow.py so the docs match what the API actually returns (§6.4).
_TRANSITION_RESPONSES = {
    200: ApplicationDetailSerializer,
    400: ErrorResponseSerializer,
    403: ErrorResponseSerializer,
    404: ErrorResponseSerializer,
}


def _error_example(
    name: str,
    *,
    code: str,
    message: str,
    status_code: str,
) -> OpenApiExample:
    return OpenApiExample(
        name,
        value={"error": {"code": code, "message": message, "details": {}}},
        response_only=True,
        status_codes=[status_code],
    )


_PERMISSION_DENIED_OWNER_EXAMPLE = _error_example(
    "Not the owner",
    code="permission_denied",
    message="Only the owner can perform this action.",
    status_code="403",
)
_PERMISSION_DENIED_REVIEWER_EXAMPLE = _error_example(
    "Not a reviewer",
    code="permission_denied",
    message="Only reviewers can perform this action.",
    status_code="403",
)
_COMMENT_REQUIRED_EXAMPLE = _error_example(
    "Comment required",
    code="comment_required",
    message="A comment is required for this transition.",
    status_code="400",
)

_REVIEWER_QUEUE_STATUSES = [
    value
    for value, _label in Application.Status.choices
    if value != Application.Status.DRAFT
]


@extend_schema(tags=["Applications"])
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
        if getattr(self, "swagger_fake_view", False):
            # drf-spectacular introspects the view with no real request; return an
            # empty queryset so it can still derive the pk type. Never hit at runtime.
            return Application.objects.none()
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

    def update(self, request: Request, *args, **kwargs) -> Response:
        # ApplicationUpdateSerializer validates and writes the editable fields,
        # but its response carries only those fields — no status, owner, or audit
        # trail. Echo the full detail shape instead so a client can cache the
        # response directly without a follow-up GET. Mirrors the transition
        # responses (submit / reviewer actions), which all return the detail read.
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        application = _detail_queryset().get(pk=instance.pk)
        return Response(ApplicationDetailSerializer(application).data)

    @extend_schema(
        summary="Submit a draft for review",
        description=(
            "Transition the applicant's own DRAFT or RETURNED application to "
            "SUBMITTED. Owner only; no request body. Writes one audit row."
        ),
        request=None,
        responses=_TRANSITION_RESPONSES,
        examples=[
            _error_example(
                "Invalid transition",
                code="invalid_transition",
                message="Only draft or returned applications can be submitted.",
                status_code="400",
            ),
            _PERMISSION_DENIED_OWNER_EXAMPLE,
        ],
    )
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


@extend_schema(tags=["Reviewer"])
@extend_schema_view(
    list=extend_schema(
        summary="List the reviewer queue",
        description=(
            "All non-draft applications, optionally filtered by status. Reviewer only."
        ),
        parameters=[
            OpenApiParameter(
                name="status",
                description="Filter the queue to a single status.",
                required=False,
                enum=_REVIEWER_QUEUE_STATUSES,
            ),
        ],
    ),
)
class ReviewerApplicationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsReviewer]

    def get_queryset(self) -> ApplicationQuerySet:
        if getattr(self, "swagger_fake_view", False):
            return Application.objects.none()
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

    @extend_schema(
        summary="Start review of a submitted application",
        description=(
            "Transition a SUBMITTED application to UNDER_REVIEW. Reviewer only; no "
            "request body."
        ),
        request=None,
        responses=_TRANSITION_RESPONSES,
        examples=[
            _error_example(
                "Invalid transition",
                code="invalid_transition",
                message="Only submitted applications can be moved under review.",
                status_code="400",
            ),
            _PERMISSION_DENIED_REVIEWER_EXAMPLE,
        ],
    )
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

    @extend_schema(
        summary="Approve an application",
        description=(
            "Transition a SUBMITTED or UNDER_REVIEW application to APPROVED "
            "(terminal). Reviewer only; no request body."
        ),
        request=None,
        responses=_TRANSITION_RESPONSES,
        examples=[
            _error_example(
                "Invalid transition",
                code="invalid_transition",
                message="Only submitted or under-review applications can be approved.",
                status_code="400",
            ),
            _PERMISSION_DENIED_REVIEWER_EXAMPLE,
        ],
    )
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

    @extend_schema(
        summary="Reject an application",
        description=(
            "Transition a SUBMITTED or UNDER_REVIEW application to REJECTED "
            "(terminal). Requires a non-blank comment. Reviewer only."
        ),
        request=TransitionCommentSerializer,
        responses=_TRANSITION_RESPONSES,
        examples=[
            _COMMENT_REQUIRED_EXAMPLE,
            _error_example(
                "Invalid transition",
                code="invalid_transition",
                message="Only submitted or under-review applications can be rejected.",
                status_code="400",
            ),
            _PERMISSION_DENIED_REVIEWER_EXAMPLE,
        ],
    )
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

    @extend_schema(
        summary="Return an application for changes",
        description=(
            "Transition a SUBMITTED or UNDER_REVIEW application to RETURNED so the "
            "owner can revise and re-submit. Requires a non-blank comment. "
            "Reviewer only."
        ),
        request=TransitionCommentSerializer,
        responses=_TRANSITION_RESPONSES,
        examples=[
            _COMMENT_REQUIRED_EXAMPLE,
            _error_example(
                "Invalid transition",
                code="invalid_transition",
                message="Only submitted or under-review applications can be returned.",
                status_code="400",
            ),
            _PERMISSION_DENIED_REVIEWER_EXAMPLE,
        ],
    )
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
