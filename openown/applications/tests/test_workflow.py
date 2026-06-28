"""
Workflow test matrix — Playbook §8.2.

Every test follows the same three-part shape:
  1. Set up state via the factory (never by assigning the status field directly).
  2. Call the service function (or assert it raises).
  3. Verify the outcome: status via refresh_from_db(), audit log count.

Legal paths: confirm the new status and exactly one new audit log.
Illegal paths: confirm status is unchanged and zero audit logs were written.
"""

import pytest

from ..models import Application
from ..services import approve_application
from ..services import reject_application
from ..services import return_application
from ..services import start_review_application
from ..services import submit_application
from ..services.exceptions import CommentRequired
from ..services.exceptions import InvalidTransition
from ..services.exceptions import WorkflowPermissionDenied
from .factories import ApplicantFactory
from .factories import ApplicationFactory
from .factories import ReviewerFactory

# ── submit_application ─────────────────────────────────────────────────────


@pytest.mark.django_db
def test_owner_submits_draft_becomes_submitted():
    applicant = ApplicantFactory()
    app = ApplicationFactory(owner=applicant, status=Application.Status.DRAFT)

    result = submit_application(application=app, actor=applicant)

    result.refresh_from_db()
    assert result.status == Application.Status.SUBMITTED
    assert result.submitted_at is not None
    assert result.audit_logs.count() == 1
    log = result.audit_logs.first()
    assert log.from_status == Application.Status.DRAFT
    assert log.to_status == Application.Status.SUBMITTED


@pytest.mark.django_db
def test_non_owner_cannot_submit_draft():
    other_applicant = ApplicantFactory()
    app = ApplicationFactory(status=Application.Status.DRAFT)
    initial_count = app.audit_logs.count()

    with pytest.raises(WorkflowPermissionDenied):
        submit_application(application=app, actor=other_applicant)

    app.refresh_from_db()
    assert app.status == Application.Status.DRAFT
    assert app.audit_logs.count() == initial_count


@pytest.mark.django_db
def test_owner_can_resubmit_returned_application():
    # A reviewer-returned application can be re-submitted by its owner — see the
    # workflow spec ("RETURNED: owner can re-submit").
    applicant = ApplicantFactory()
    app = ApplicationFactory(owner=applicant, status=Application.Status.RETURNED)

    result = submit_application(application=app, actor=applicant)

    result.refresh_from_db()
    assert result.status == Application.Status.SUBMITTED
    assert result.audit_logs.count() == 1
    log = result.audit_logs.first()
    assert log.from_status == Application.Status.RETURNED
    assert log.to_status == Application.Status.SUBMITTED


@pytest.mark.django_db
def test_owner_cannot_submit_in_review_or_terminal():
    applicant = ApplicantFactory()
    app = ApplicationFactory(owner=applicant, status=Application.Status.SUBMITTED)

    with pytest.raises(InvalidTransition):
        submit_application(application=app, actor=applicant)

    app.refresh_from_db()
    assert app.status == Application.Status.SUBMITTED
    assert app.audit_logs.count() == 0


# ── start_review_application ───────────────────────────────────────────────


@pytest.mark.django_db
def test_reviewer_starts_review_from_submitted():
    reviewer = ReviewerFactory()
    app = ApplicationFactory(status=Application.Status.SUBMITTED)

    result = start_review_application(application=app, actor=reviewer)

    result.refresh_from_db()
    assert result.status == Application.Status.UNDER_REVIEW
    assert result.audit_logs.count() == 1


@pytest.mark.django_db
def test_reviewer_cannot_start_review_from_draft():
    reviewer = ReviewerFactory()
    app = ApplicationFactory(status=Application.Status.DRAFT)

    with pytest.raises(InvalidTransition):
        start_review_application(application=app, actor=reviewer)

    app.refresh_from_db()
    assert app.status == Application.Status.DRAFT
    assert app.audit_logs.count() == 0


# ── approve_application ────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize(
    "from_status",
    [Application.Status.SUBMITTED, Application.Status.UNDER_REVIEW],
)
def test_reviewer_approves_submitted_or_under_review(from_status):
    reviewer = ReviewerFactory()
    app = ApplicationFactory(status=from_status)

    result = approve_application(application=app, actor=reviewer)

    result.refresh_from_db()
    assert result.status == Application.Status.APPROVED
    assert result.reviewed_at is not None
    assert result.audit_logs.count() == 1


@pytest.mark.django_db
def test_applicant_cannot_approve():
    applicant = ApplicantFactory()
    app = ApplicationFactory(owner=applicant, status=Application.Status.SUBMITTED)

    with pytest.raises(WorkflowPermissionDenied):
        approve_application(application=app, actor=applicant)

    app.refresh_from_db()
    assert app.status == Application.Status.SUBMITTED
    assert app.audit_logs.count() == 0


# ── reject_application ─────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize(
    "from_status",
    [Application.Status.SUBMITTED, Application.Status.UNDER_REVIEW],
)
def test_reviewer_rejects_submitted_or_under_review_with_comment(from_status):
    reviewer = ReviewerFactory()
    app = ApplicationFactory(status=from_status)

    result = reject_application(
        application=app,
        actor=reviewer,
        comment="Not compliant.",
    )

    result.refresh_from_db()
    assert result.status == Application.Status.REJECTED
    assert result.audit_logs.count() == 1
    log = result.audit_logs.first()
    assert log.from_status == from_status
    assert log.to_status == Application.Status.REJECTED
    assert log.comment == "Not compliant."


@pytest.mark.django_db
def test_reviewer_cannot_reject_without_comment():
    reviewer = ReviewerFactory()
    app = ApplicationFactory(status=Application.Status.SUBMITTED)

    with pytest.raises(CommentRequired):
        reject_application(application=app, actor=reviewer, comment="   ")

    app.refresh_from_db()
    assert app.status == Application.Status.SUBMITTED
    assert app.audit_logs.count() == 0


# ── return_application ─────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize(
    "from_status",
    [Application.Status.SUBMITTED, Application.Status.UNDER_REVIEW],
)
def test_reviewer_returns_submitted_or_under_review_with_comment(from_status):
    reviewer = ReviewerFactory()
    app = ApplicationFactory(status=from_status)

    result = return_application(
        application=app,
        actor=reviewer,
        comment="Needs revision.",
    )

    result.refresh_from_db()
    assert result.status == Application.Status.RETURNED
    assert result.reviewed_at is not None
    assert result.audit_logs.count() == 1
    log = result.audit_logs.first()
    assert log.from_status == from_status
    assert log.to_status == Application.Status.RETURNED
    assert log.comment == "Needs revision."


@pytest.mark.django_db
def test_reviewer_cannot_return_without_comment():
    reviewer = ReviewerFactory()
    app = ApplicationFactory(status=Application.Status.UNDER_REVIEW)

    with pytest.raises(CommentRequired):
        return_application(application=app, actor=reviewer, comment="")

    app.refresh_from_db()
    assert app.status == Application.Status.UNDER_REVIEW
    assert app.audit_logs.count() == 0


# ── Terminal state invariants ──────────────────────────────────────────────


@pytest.mark.django_db
def test_cannot_mutate_approved_application():
    reviewer = ReviewerFactory()
    app = ApplicationFactory(status=Application.Status.APPROVED)
    prior_log_count = app.audit_logs.count()

    with pytest.raises(InvalidTransition):
        approve_application(application=app, actor=reviewer)

    app.refresh_from_db()
    assert app.status == Application.Status.APPROVED
    assert app.audit_logs.count() == prior_log_count


@pytest.mark.django_db
def test_cannot_mutate_rejected_application():
    reviewer = ReviewerFactory()
    app = ApplicationFactory(status=Application.Status.REJECTED)
    prior_log_count = app.audit_logs.count()

    with pytest.raises(InvalidTransition):
        approve_application(application=app, actor=reviewer)

    app.refresh_from_db()
    assert app.status == Application.Status.REJECTED
    assert app.audit_logs.count() == prior_log_count
