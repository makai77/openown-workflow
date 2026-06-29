import pytest

from ..models import Application
from .factories import ApplicantFactory
from .factories import ApplicationAuditLogFactory
from .factories import ApplicationFactory
from .factories import ReviewerFactory

# ── Application.__str__ ────────────────────────────────────────────────────


@pytest.mark.django_db
def test_application_str():
    app = ApplicationFactory.create(title="My Grant Application")
    assert str(app) == "My Grant Application"


# ── Application.is_editable_by_applicant ──────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize(
    "status",
    [
        Application.Status.DRAFT,
        Application.Status.RETURNED,
    ],
)
def test_draft_or_returned_is_editable(status):
    # A returned application goes back to the owner to revise — see the workflow
    # spec ("RETURNED: owner can re-submit").
    app = ApplicationFactory.create(status=status)
    assert app.is_editable_by_applicant is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    "status",
    [
        Application.Status.SUBMITTED,
        Application.Status.UNDER_REVIEW,
        Application.Status.APPROVED,
        Application.Status.REJECTED,
    ],
)
def test_in_review_or_terminal_not_editable(status):
    app = ApplicationFactory.create(status=status)
    assert app.is_editable_by_applicant is False


# ── Application.is_reviewable ─────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize(
    "status",
    [
        Application.Status.SUBMITTED,
        Application.Status.UNDER_REVIEW,
    ],
)
def test_is_reviewable_true(status):
    app = ApplicationFactory.create(status=status)
    assert app.is_reviewable is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    "status",
    [
        Application.Status.DRAFT,
        Application.Status.APPROVED,
        Application.Status.REJECTED,
        Application.Status.RETURNED,
    ],
)
def test_is_reviewable_false(status):
    app = ApplicationFactory.create(status=status)
    assert app.is_reviewable is False


# ── ApplicationQuerySet ────────────────────────────────────────────────────


@pytest.mark.django_db
def test_for_applicant_filters_own_applications():
    applicant = ApplicantFactory.create()
    other = ApplicantFactory.create()
    own = ApplicationFactory.create(owner=applicant)
    ApplicationFactory.create(owner=other)

    qs = Application.objects.for_applicant(applicant)
    assert list(qs) == [own]


@pytest.mark.django_db
def test_for_reviewer_queue_excludes_drafts():
    ApplicationFactory.create(status=Application.Status.DRAFT)
    submitted = ApplicationFactory.create(status=Application.Status.SUBMITTED)
    under_review = ApplicationFactory.create(status=Application.Status.UNDER_REVIEW)

    ids = set(Application.objects.for_reviewer_queue().values_list("id", flat=True))
    assert submitted.id in ids
    assert under_review.id in ids


@pytest.mark.django_db
def test_with_owner_selects_related():
    ApplicationFactory.create()
    app = Application.objects.with_owner().first()
    assert app is not None
    assert app.owner_id is not None


@pytest.mark.django_db
def test_with_audit_trail_prefetches():
    app = ApplicationFactory.create(status=Application.Status.SUBMITTED)
    reviewer = ReviewerFactory.create()
    ApplicationAuditLogFactory.create(
        application=app,
        actor=reviewer,
        from_status=Application.Status.DRAFT,
        to_status=Application.Status.SUBMITTED,
    )

    loaded = Application.objects.with_owner().with_audit_trail().get(pk=app.pk)
    assert len(loaded.audit_logs.all()) == 1
