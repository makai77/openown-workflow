"""
Mandatory authorization test — Playbook §8.3 / project brief.

An applicant calling a reviewer transition endpoint directly must be rejected with
403 by the permission layer, and the application status must be unchanged. This is
the explicit "authorization is tested, not assumed" requirement.
"""

from http import HTTPStatus

import pytest

from ..models import Application
from .factories import ApplicantFactory
from .factories import ApplicationFactory
from .factories import ReviewerFactory


@pytest.mark.django_db
def test_applicant_cannot_approve_via_direct_api_call(api_client):
    applicant = ApplicantFactory()
    application = ApplicationFactory(status=Application.Status.SUBMITTED)
    api_client.force_authenticate(applicant)

    response = api_client.post(
        f"/api/reviewer/applications/{application.id}/approve/",
        {},
        format="json",
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.data["error"]["code"] == "permission_denied"
    application.refresh_from_db()
    assert application.status == Application.Status.SUBMITTED
    assert application.audit_logs.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    "action_name",
    ["start-review", "approve", "reject", "return"],
)
def test_applicant_is_forbidden_from_every_reviewer_transition(api_client, action_name):
    applicant = ApplicantFactory()
    application = ApplicationFactory(status=Application.Status.SUBMITTED)
    api_client.force_authenticate(applicant)

    response = api_client.post(
        f"/api/reviewer/applications/{application.id}/{action_name}/",
        {"comment": "trying anyway"},
        format="json",
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    application.refresh_from_db()
    assert application.status == Application.Status.SUBMITTED
    assert application.audit_logs.count() == 0


@pytest.mark.django_db
def test_reviewer_cannot_create_application(api_client):
    # The applicant create endpoint is gated by IsApplicant; a reviewer is rejected.
    reviewer = ReviewerFactory()
    api_client.force_authenticate(reviewer)

    response = api_client.post(
        "/api/applications/",
        {"title": "Reviewer app", "category": "GENERAL"},
        format="json",
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert Application.objects.count() == 0
