from django.db import transaction
from django.utils import timezone

from ..models import Application
from ..models import ApplicationAuditLog
from .exceptions import CommentRequired
from .exceptions import InvalidTransition
from .exceptions import WorkflowPermissionDenied


def submit_application(*, application: Application, actor) -> Application:
    with transaction.atomic():
        application = _locked_application(application)
        _require_owner(application=application, actor=actor)
        _require_status(
            application=application,
            allowed={Application.Status.DRAFT, Application.Status.RETURNED},
            message="Only draft or returned applications can be submitted.",
        )
        return _transition(
            application=application,
            actor=actor,
            to_status=Application.Status.SUBMITTED,
            submitted=True,
        )


def start_review_application(*, application: Application, actor) -> Application:
    with transaction.atomic():
        application = _locked_application(application)
        _require_reviewer(actor=actor)
        _require_status(
            application=application,
            allowed={Application.Status.SUBMITTED},
            message="Only submitted applications can be moved under review.",
        )
        return _transition(
            application=application,
            actor=actor,
            to_status=Application.Status.UNDER_REVIEW,
        )


def approve_application(*, application: Application, actor) -> Application:
    with transaction.atomic():
        application = _locked_application(application)
        _require_reviewer(actor=actor)
        _require_status(
            application=application,
            allowed={Application.Status.SUBMITTED, Application.Status.UNDER_REVIEW},
            message="Only submitted or under-review applications can be approved.",
        )
        return _transition(
            application=application,
            actor=actor,
            to_status=Application.Status.APPROVED,
            reviewed=True,
        )


def reject_application(*, application: Application, actor, comment: str) -> Application:
    with transaction.atomic():
        application = _locked_application(application)
        _require_reviewer(actor=actor)
        _require_status(
            application=application,
            allowed={Application.Status.SUBMITTED, Application.Status.UNDER_REVIEW},
            message="Only submitted or under-review applications can be rejected.",
        )
        comment = _require_comment(comment=comment)
        return _transition(
            application=application,
            actor=actor,
            to_status=Application.Status.REJECTED,
            comment=comment,
            reviewed=True,
        )


def return_application(*, application: Application, actor, comment: str) -> Application:
    with transaction.atomic():
        application = _locked_application(application)
        _require_reviewer(actor=actor)
        _require_status(
            application=application,
            allowed={Application.Status.SUBMITTED, Application.Status.UNDER_REVIEW},
            message="Only submitted or under-review applications can be returned.",
        )
        comment = _require_comment(comment=comment)
        return _transition(
            application=application,
            actor=actor,
            to_status=Application.Status.RETURNED,
            comment=comment,
            reviewed=True,
        )


# ── Private helpers ────────────────────────────────────────────────────────


def _locked_application(application: Application) -> Application:
    # Returns a BARE re-fetched instance (no select_related / prefetch) locked
    # FOR UPDATE. The transition functions hand this object back, so a caller that
    # serializes it for a detail response must re-fetch the pk through the
    # ViewSet's _detail_queryset() (.with_owner().with_audit_trail()) rather than
    # serialize this value directly — otherwise owner + audit_logs lazy-load and
    # break the fixed query budget.
    return Application.objects.select_for_update().get(pk=application.pk)


def _require_owner(*, application: Application, actor) -> None:
    if not actor.is_authenticated or application.owner_id != actor.id:
        raise WorkflowPermissionDenied("Only the owner can perform this action.")


def _require_reviewer(*, actor) -> None:
    if not actor.is_authenticated or not actor.is_reviewer:
        raise WorkflowPermissionDenied("Only reviewers can perform this action.")


def _require_status(
    *,
    application: Application,
    allowed: set[str],
    message: str,
) -> None:
    if application.status not in allowed:
        raise InvalidTransition(message)


def _require_comment(*, comment: str) -> str:
    cleaned = comment.strip()
    if not cleaned:
        raise CommentRequired("A comment is required for this transition.")
    return cleaned


def _transition(
    *,
    application: Application,
    actor,
    to_status: str,
    comment: str = "",
    submitted: bool = False,
    reviewed: bool = False,
) -> Application:
    old_status = application.status
    now = timezone.now()
    application.status = to_status
    update_fields = ["status", "updated_at"]
    if submitted:
        application.submitted_at = now
        update_fields.append("submitted_at")
    if reviewed:
        application.reviewed_at = now
        update_fields.append("reviewed_at")
    application.save(update_fields=update_fields)
    ApplicationAuditLog.objects.create(
        application=application,
        actor=actor,
        from_status=old_status,
        to_status=to_status,
        comment=comment,
    )
    return application
