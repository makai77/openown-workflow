"""
Reviewer API matrix — Playbook §8.3.

Each rejected action asserts the status code AND that the application state is
untouched (status unchanged, no new audit rows). State is built with factories.
"""

from http import HTTPStatus

import pytest

from ..models import Application
from .factories import ApplicantFactory
from .factories import ApplicationFactory
from .factories import ReviewerFactory

QUEUE_URL = "/api/reviewer/applications/"


def action_url(pk, name):
    return f"/api/reviewer/applications/{pk}/{name}/"


# ── queue access & filtering ───────────────────────────────────────────────


@pytest.mark.django_db
def test_applicant_cannot_access_reviewer_queue(api_client):
    applicant = ApplicantFactory.create()
    api_client.force_authenticate(applicant)

    response = api_client.get(QUEUE_URL)

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.data["error"]["code"] == "permission_denied"


@pytest.mark.django_db
def test_reviewer_queue_excludes_drafts(api_client):
    reviewer = ReviewerFactory.create()
    ApplicationFactory.create(status=Application.Status.DRAFT)  # private to its owner
    submitted = ApplicationFactory.create(status=Application.Status.SUBMITTED)
    api_client.force_authenticate(reviewer)

    response = api_client.get(QUEUE_URL)

    assert response.status_code == HTTPStatus.OK
    ids = [row["id"] for row in response.data["results"]]
    assert ids == [submitted.id]


@pytest.mark.django_db
def test_reviewer_queue_filterable_by_status(api_client):
    reviewer = ReviewerFactory.create()
    submitted = ApplicationFactory.create(status=Application.Status.SUBMITTED)
    ApplicationFactory.create(status=Application.Status.UNDER_REVIEW)
    api_client.force_authenticate(reviewer)

    response = api_client.get(QUEUE_URL, {"status": Application.Status.SUBMITTED})

    assert response.status_code == HTTPStatus.OK
    ids = [row["id"] for row in response.data["results"]]
    assert ids == [submitted.id]


# ── legal transitions ──────────────────────────────────────────────────────


@pytest.mark.django_db
def test_reviewer_starts_review(api_client):
    reviewer = ReviewerFactory.create()
    application = ApplicationFactory.create(status=Application.Status.SUBMITTED)
    api_client.force_authenticate(reviewer)

    response = api_client.post(
        action_url(application.id, "start-review"),
        {},
        format="json",
    )

    assert response.status_code == HTTPStatus.OK
    assert response.data["status"] == Application.Status.UNDER_REVIEW


@pytest.mark.django_db
def test_reviewer_approves_submitted(api_client):
    reviewer = ReviewerFactory.create()
    application = ApplicationFactory.create(status=Application.Status.SUBMITTED)
    api_client.force_authenticate(reviewer)

    response = api_client.post(action_url(application.id, "approve"), {}, format="json")

    assert response.status_code == HTTPStatus.OK
    assert response.data["status"] == Application.Status.APPROVED
    assert any(
        row["to_status"] == Application.Status.APPROVED
        for row in response.data["audit_logs"]
    )


@pytest.mark.django_db
def test_reviewer_rejects_with_comment(api_client):
    reviewer = ReviewerFactory.create()
    application = ApplicationFactory.create(status=Application.Status.UNDER_REVIEW)
    api_client.force_authenticate(reviewer)

    response = api_client.post(
        action_url(application.id, "reject"),
        {"comment": "Insufficient detail."},
        format="json",
    )

    assert response.status_code == HTTPStatus.OK
    assert response.data["status"] == Application.Status.REJECTED
    assert response.data["audit_logs"][-1]["comment"] == "Insufficient detail."


@pytest.mark.django_db
def test_reviewer_returns_with_comment(api_client):
    reviewer = ReviewerFactory.create()
    application = ApplicationFactory.create(status=Application.Status.SUBMITTED)
    api_client.force_authenticate(reviewer)

    response = api_client.post(
        action_url(application.id, "return"),
        {"comment": "Please revise section 2."},
        format="json",
    )

    assert response.status_code == HTTPStatus.OK
    assert response.data["status"] == Application.Status.RETURNED


# ── rejected transitions (status code + untouched state) ───────────────────


@pytest.mark.django_db
def test_reject_without_comment_is_rejected(api_client):
    reviewer = ReviewerFactory.create()
    application = ApplicationFactory.create(status=Application.Status.SUBMITTED)
    api_client.force_authenticate(reviewer)

    response = api_client.post(action_url(application.id, "reject"), {}, format="json")

    assert response.status_code == HTTPStatus.BAD_REQUEST
    application.refresh_from_db()
    assert application.status == Application.Status.SUBMITTED
    assert application.audit_logs.count() == 0


@pytest.mark.django_db
def test_return_without_comment_is_rejected(api_client):
    reviewer = ReviewerFactory.create()
    application = ApplicationFactory.create(status=Application.Status.SUBMITTED)
    api_client.force_authenticate(reviewer)

    response = api_client.post(action_url(application.id, "return"), {}, format="json")

    assert response.status_code == HTTPStatus.BAD_REQUEST
    application.refresh_from_db()
    assert application.status == Application.Status.SUBMITTED
    assert application.audit_logs.count() == 0


@pytest.mark.django_db
def test_reviewer_cannot_act_on_draft(api_client):
    # A draft is not in the reviewer queue, so it is invisible → 404, not 400.
    # This is stronger than §8.3's "approve draft → 400": drafts stay private.
    reviewer = ReviewerFactory.create()
    application = ApplicationFactory.create(status=Application.Status.DRAFT)
    api_client.force_authenticate(reviewer)

    response = api_client.post(action_url(application.id, "approve"), {}, format="json")

    assert response.status_code == HTTPStatus.NOT_FOUND
    application.refresh_from_db()
    assert application.status == Application.Status.DRAFT
    assert application.audit_logs.count() == 0


@pytest.mark.django_db
def test_start_review_on_under_review_is_invalid_transition(api_client):
    reviewer = ReviewerFactory.create()
    application = ApplicationFactory.create(status=Application.Status.UNDER_REVIEW)
    api_client.force_authenticate(reviewer)

    response = api_client.post(
        action_url(application.id, "start-review"),
        {},
        format="json",
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.data["error"]["code"] == "invalid_transition"
    application.refresh_from_db()
    assert application.status == Application.Status.UNDER_REVIEW
    assert application.audit_logs.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("action_name", ["reject", "return"])
def test_commented_transition_on_terminal_app_is_invalid(api_client, action_name):
    # A valid comment passes the serializer, so the service is reached and rejects
    # the transition on a terminal (APPROVED) application → invalid_transition.
    reviewer = ReviewerFactory.create()
    application = ApplicationFactory.create(status=Application.Status.APPROVED)
    api_client.force_authenticate(reviewer)

    response = api_client.post(
        action_url(application.id, action_name),
        {"comment": "should not apply"},
        format="json",
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.data["error"]["code"] == "invalid_transition"
    application.refresh_from_db()
    assert application.status == Application.Status.APPROVED
    assert application.audit_logs.count() == 0


@pytest.mark.django_db
def test_post_to_reviewer_queue_is_method_not_allowed(api_client):
    # The read-only queue rejects writes with 405, still wrapped in the contract
    # envelope rather than DRF's bare {"detail": ...}.
    reviewer = ReviewerFactory.create()
    api_client.force_authenticate(reviewer)

    response = api_client.post(QUEUE_URL, {}, format="json")

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert response.data["error"]["code"] == "method_not_allowed"


@pytest.mark.django_db
def test_approving_terminal_application_is_invalid_transition(api_client):
    # The genuine 400 invalid_transition path: a visible (non-draft) application
    # in a state the transition does not allow.
    reviewer = ReviewerFactory.create()
    application = ApplicationFactory.create(status=Application.Status.APPROVED)
    api_client.force_authenticate(reviewer)

    response = api_client.post(action_url(application.id, "approve"), {}, format="json")

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.data["error"]["code"] == "invalid_transition"
    application.refresh_from_db()
    assert application.status == Application.Status.APPROVED
    # No transition row was written for the rejected approve (the seed APPROVED
    # state was created by the factory, not by a transition).
    assert application.audit_logs.count() == 0
