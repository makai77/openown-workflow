from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from ..models import Application
from ..models import ApplicationAuditLog
from .exceptions import CommentRequired
from .exceptions import InvalidTransition
from .exceptions import WorkflowPermissionDenied

if TYPE_CHECKING:
    from openown.users.models import User


# The single authority for which statuses each reviewer action is legal from.
# Both the transition functions (via _require_status) and available_actions()
# read from this mapping — the rule lives in exactly one place and cannot drift.
# Insertion order is the order available_actions() returns the keys in.
_REVIEWER_ACTION_STATUSES: dict[str, set[str]] = {
    "start_review": {Application.Status.SUBMITTED},
    "approve": {Application.Status.SUBMITTED, Application.Status.UNDER_REVIEW},
    "reject": {Application.Status.SUBMITTED, Application.Status.UNDER_REVIEW},
    "return": {Application.Status.SUBMITTED, Application.Status.UNDER_REVIEW},
}

# Public, ordered tuple of the reviewer-action keys — the closed vocabulary that
# available_actions() can return and that the OpenAPI schema enumerates.
REVIEWER_ACTION_KEYS: tuple[str, ...] = tuple(_REVIEWER_ACTION_STATUSES)


def available_actions(*, application: Application, actor: User) -> list[str]:
    # The single read-only authority for "what can this actor do to this
    # application right now". Reuses the same predicates the transition functions
    # use (_is_reviewer + _REVIEWER_ACTION_STATUSES), so it can never disagree
    # with what those functions will actually allow. Pure: no DB writes, no
    # side effects — operates on the already-loaded object + actor.
    if not _is_reviewer(actor=actor):
        return []
    return [
        action
        for action, allowed in _REVIEWER_ACTION_STATUSES.items()
        if application.status in allowed
    ]


def submit_application(*, application: Application, actor: User) -> Application:
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


def start_review_application(*, application: Application, actor: User) -> Application:
    with transaction.atomic():
        application = _locked_application(application)
        _require_reviewer(actor=actor)
        _require_status(
            application=application,
            allowed=_REVIEWER_ACTION_STATUSES["start_review"],
            message="Only submitted applications can be moved under review.",
        )
        return _transition(
            application=application,
            actor=actor,
            to_status=Application.Status.UNDER_REVIEW,
        )


def approve_application(*, application: Application, actor: User) -> Application:
    with transaction.atomic():
        application = _locked_application(application)
        _require_reviewer(actor=actor)
        _require_status(
            application=application,
            allowed=_REVIEWER_ACTION_STATUSES["approve"],
            message="Only submitted or under-review applications can be approved.",
        )
        return _transition(
            application=application,
            actor=actor,
            to_status=Application.Status.APPROVED,
            reviewed=True,
        )


def reject_application(
    *,
    application: Application,
    actor: User,
    comment: str,
) -> Application:
    with transaction.atomic():
        application = _locked_application(application)
        _require_reviewer(actor=actor)
        _require_status(
            application=application,
            allowed=_REVIEWER_ACTION_STATUSES["reject"],
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


def return_application(
    *,
    application: Application,
    actor: User,
    comment: str,
) -> Application:
    with transaction.atomic():
        application = _locked_application(application)
        _require_reviewer(actor=actor)
        _require_status(
            application=application,
            allowed=_REVIEWER_ACTION_STATUSES["return"],
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


def _require_owner(*, application: Application, actor: User) -> None:
    # `owner_id` is Django's auto-generated FK column accessor — compared directly
    # so we never fetch the owner row (preserving the query budget). Pyrefly lacks
    # Django ORM model introspection and can't see it; mypy's django-stubs plugin
    # can, so this suppression is pyrefly-only.
    if not actor.is_authenticated or application.owner_id != actor.id:  # pyrefly: ignore[missing-attribute]
        raise WorkflowPermissionDenied("Only the owner can perform this action.")


def _is_reviewer(*, actor: User) -> bool:
    # The boolean predicate behind reviewer access. _require_reviewer wraps it for
    # the transition functions; available_actions() reads it directly. One rule,
    # two readers — they cannot disagree on who is a reviewer.
    return actor.is_authenticated and actor.is_reviewer


def _require_reviewer(*, actor: User) -> None:
    if not _is_reviewer(actor=actor):
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
    actor: User,
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
