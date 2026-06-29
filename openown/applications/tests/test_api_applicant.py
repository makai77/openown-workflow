"""
Applicant API matrix — Playbook §8.3.

Every test asserts BOTH the status code AND the side effect (object created/edited,
status unchanged, or zero audit rows on a rejected action). State is built with the
factories — never by assigning the status field or via Model.objects.create.
"""

from http import HTTPStatus

import pytest

from ..models import Application
from .factories import ApplicantFactory
from .factories import ApplicationFactory

LIST_URL = "/api/applications/"


def detail_url(pk):
    return f"/api/applications/{pk}/"


def submit_url(pk):
    return f"/api/applications/{pk}/submit/"


# ── read access & visibility ───────────────────────────────────────────────


@pytest.mark.django_db
def test_anonymous_list_is_unauthorized(api_client):
    response = api_client.get(LIST_URL)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.data["error"]["code"] == "not_authenticated"


@pytest.mark.django_db
def test_applicant_list_returns_only_own_applications(api_client):
    owner = ApplicantFactory.create()
    other = ApplicantFactory.create()
    mine = ApplicationFactory.create(owner=owner)
    ApplicationFactory.create(owner=other)  # must not appear
    api_client.force_authenticate(owner)

    response = api_client.get(LIST_URL)

    assert response.status_code == HTTPStatus.OK
    ids = [row["id"] for row in response.data["results"]]
    assert ids == [mine.id]


@pytest.mark.django_db
def test_applicant_cannot_see_another_applicants_application(api_client):
    owner = ApplicantFactory.create()
    other = ApplicationFactory.create(owner=ApplicantFactory.create())
    api_client.force_authenticate(owner)

    response = api_client.get(detail_url(other.id))

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.data["error"]["code"] == "not_found"


# ── create ─────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_applicant_creates_draft(api_client):
    applicant = ApplicantFactory.create()
    api_client.force_authenticate(applicant)

    response = api_client.post(
        LIST_URL,
        {"title": "New app", "category": "GENERAL", "amount": "500.00"},
        format="json",
    )

    assert response.status_code == HTTPStatus.CREATED
    assert response.data["status"] == Application.Status.DRAFT
    application = Application.objects.get(pk=response.data["id"])
    assert application.owner == applicant


@pytest.mark.django_db
def test_create_ignores_client_supplied_owner_and_status(api_client):
    applicant = ApplicantFactory.create()
    other = ApplicantFactory.create()
    api_client.force_authenticate(applicant)

    response = api_client.post(
        LIST_URL,
        {
            "title": "Spoofed",
            "category": "GENERAL",
            "status": Application.Status.APPROVED,
            "owner": other.id,
        },
        format="json",
    )

    assert response.status_code == HTTPStatus.CREATED
    application = Application.objects.get(pk=response.data["id"])
    # status and owner are backend-assigned, never trusted from the client.
    assert application.status == Application.Status.DRAFT
    assert application.owner == applicant


# ── edit ───────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_applicant_edits_own_draft(api_client):
    applicant = ApplicantFactory.create()
    application = ApplicationFactory.create(
        owner=applicant,
        status=Application.Status.DRAFT,
        title="Before",
    )
    api_client.force_authenticate(applicant)

    response = api_client.patch(
        detail_url(application.id),
        {"title": "After"},
        format="json",
    )

    assert response.status_code == HTTPStatus.OK
    application.refresh_from_db()
    assert application.title == "After"


@pytest.mark.django_db
def test_applicant_can_edit_returned_application(api_client):
    # Pins the RETURNED-is-editable decision: a returned application goes back to
    # the owner to revise before re-submitting (is_editable_by_applicant).
    applicant = ApplicantFactory.create()
    application = ApplicationFactory.create(
        owner=applicant,
        status=Application.Status.RETURNED,
        title="Before",
    )
    api_client.force_authenticate(applicant)

    response = api_client.patch(
        detail_url(application.id),
        {"title": "Revised"},
        format="json",
    )

    assert response.status_code == HTTPStatus.OK
    application.refresh_from_db()
    assert application.title == "Revised"


@pytest.mark.django_db
def test_applicant_cannot_edit_submitted_application(api_client):
    applicant = ApplicantFactory.create()
    application = ApplicationFactory.create(
        owner=applicant,
        status=Application.Status.SUBMITTED,
        title="Locked",
    )
    api_client.force_authenticate(applicant)

    response = api_client.patch(
        detail_url(application.id),
        {"title": "Hacked"},
        format="json",
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.data["error"]["code"] == "validation_error"
    application.refresh_from_db()
    assert application.title == "Locked"


# ── submit ─────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_applicant_submits_own_draft(api_client):
    applicant = ApplicantFactory.create()
    application = ApplicationFactory.create(
        owner=applicant,
        status=Application.Status.DRAFT,
    )
    api_client.force_authenticate(applicant)

    response = api_client.post(submit_url(application.id), {}, format="json")

    assert response.status_code == HTTPStatus.OK
    assert response.data["status"] == Application.Status.SUBMITTED
    # The audit row is visible in the transition response.
    assert len(response.data["audit_logs"]) == 1
    assert response.data["audit_logs"][0]["to_status"] == Application.Status.SUBMITTED
    application.refresh_from_db()
    assert application.audit_logs.count() == 1


@pytest.mark.django_db
def test_submitting_non_draft_is_invalid_transition(api_client):
    # The submit error path through the service: a SUBMITTED application owned by
    # the caller is visible (owner filter) but not in a submittable state.
    applicant = ApplicantFactory.create()
    application = ApplicationFactory.create(
        owner=applicant,
        status=Application.Status.SUBMITTED,
    )
    api_client.force_authenticate(applicant)

    response = api_client.post(submit_url(application.id), {}, format="json")

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.data["error"]["code"] == "invalid_transition"
    application.refresh_from_db()
    assert application.status == Application.Status.SUBMITTED
    assert application.audit_logs.count() == 0


@pytest.mark.django_db
def test_applicant_cannot_delete_application(api_client):
    # Destroy is intentionally not exposed: deleting an application would erase its
    # audit trail. The viewset omits DestroyModelMixin → 405.
    applicant = ApplicantFactory.create()
    application = ApplicationFactory.create(
        owner=applicant,
        status=Application.Status.DRAFT,
    )
    api_client.force_authenticate(applicant)

    response = api_client.delete(detail_url(application.id))

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert Application.objects.filter(pk=application.id).exists()


@pytest.mark.django_db
def test_applicant_cannot_submit_another_users_draft(api_client):
    owner = ApplicantFactory.create()
    attacker = ApplicantFactory.create()
    application = ApplicationFactory.create(
        owner=owner,
        status=Application.Status.DRAFT,
    )
    api_client.force_authenticate(attacker)

    response = api_client.post(submit_url(application.id), {}, format="json")

    # Owner-filtered queryset hides the object entirely → 404 (§8.3: 403/404).
    assert response.status_code == HTTPStatus.NOT_FOUND
    application.refresh_from_db()
    assert application.status == Application.Status.DRAFT
    assert application.audit_logs.count() == 0
