import pytest

from openown.applications.models import Application
from openown.users.models import User
from openown.users.tests.factories import UserFactory

from .factories import ApplicantFactory
from .factories import ApplicationAuditLogFactory
from .factories import ApplicationFactory
from .factories import ReviewerFactory

# ── User role properties ───────────────────────────────────────────────────


@pytest.mark.django_db
def test_user_is_applicant_true():
    user = ApplicantFactory()
    assert user.is_applicant is True
    assert user.is_reviewer is False


@pytest.mark.django_db
def test_user_is_reviewer_true():
    user = ReviewerFactory()
    assert user.is_reviewer is True
    assert user.is_applicant is False


@pytest.mark.django_db
def test_user_role_defaults_to_applicant():
    user = UserFactory()
    assert user.role == User.Role.APPLICANT
    assert user.is_applicant is True


# ── Application.__str__ ────────────────────────────────────────────────────


@pytest.mark.django_db
def test_application_str():
    app = ApplicationFactory(title="My Grant Application")
    assert str(app) == "My Grant Application"


# ── Application.is_editable_by_applicant ──────────────────────────────────


@pytest.mark.django_db
def test_draft_is_editable():
    app = ApplicationFactory(status=Application.Status.DRAFT)
    assert app.is_editable_by_applicant is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    "status",
    [
        Application.Status.SUBMITTED,
        Application.Status.UNDER_REVIEW,
        Application.Status.APPROVED,
        Application.Status.REJECTED,
        Application.Status.RETURNED,
    ],
)
def test_non_draft_not_editable(status):
    app = ApplicationFactory(status=status)
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
    app = ApplicationFactory(status=status)
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
    app = ApplicationFactory(status=status)
    assert app.is_reviewable is False


# ── ApplicationQuerySet ────────────────────────────────────────────────────


@pytest.mark.django_db
def test_for_applicant_filters_own_applications():
    applicant = ApplicantFactory()
    other = ApplicantFactory()
    own = ApplicationFactory(owner=applicant)
    ApplicationFactory(owner=other)

    qs = Application.objects.for_applicant(applicant)
    assert list(qs) == [own]


@pytest.mark.django_db
def test_for_reviewer_queue_excludes_drafts():
    ApplicationFactory(status=Application.Status.DRAFT)
    submitted = ApplicationFactory(status=Application.Status.SUBMITTED)
    under_review = ApplicationFactory(status=Application.Status.UNDER_REVIEW)

    ids = set(Application.objects.for_reviewer_queue().values_list("id", flat=True))
    assert submitted.id in ids
    assert under_review.id in ids


@pytest.mark.django_db
def test_with_owner_selects_related():
    ApplicationFactory()
    app = Application.objects.with_owner().first()
    assert app is not None
    assert app.owner_id is not None


@pytest.mark.django_db
def test_with_audit_trail_prefetches():
    app = ApplicationFactory(status=Application.Status.SUBMITTED)
    reviewer = ReviewerFactory()
    ApplicationAuditLogFactory(
        application=app,
        actor=reviewer,
        from_status=Application.Status.DRAFT,
        to_status=Application.Status.SUBMITTED,
    )

    loaded = Application.objects.with_owner().with_audit_trail().get(pk=app.pk)
    assert len(loaded.audit_logs.all()) == 1
