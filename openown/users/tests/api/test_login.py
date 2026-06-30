from http import HTTPStatus

import pytest
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from openown.applications.tests.factories import ApplicantFactory
from openown.users.tests.factories import UserFactory


@pytest.mark.django_db
def test_token_auth_takes_precedence_over_session_cookie_on_writes():
    """A token-authenticated write must succeed even when the browser also carries
    a Django session cookie.

    TokenAuthentication is ordered before SessionAuthentication, so the token header
    authenticates first and no session is used — keeping SessionAuthentication's CSRF
    enforcement off the SPA's writes. If the order regressed, SessionAuthentication
    would authenticate the session and 403 this (CSRF-token-less) POST.
    """
    applicant = ApplicantFactory.create()
    token = Token.objects.create(user=applicant)

    client = APIClient(enforce_csrf_checks=True)
    client.force_login(applicant)  # plants the session cookie
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    response = client.post(
        "/api/applications/",
        {"title": "New app", "category": "GENERAL", "amount": "500.00"},
        format="json",
    )

    assert response.status_code == HTTPStatus.CREATED


@pytest.mark.django_db
def test_login_succeeds_with_active_session_cookie():
    """A browser holding a Django session cookie (e.g. from /admin on the same
    origin) must still be able to obtain a token.

    With SessionAuthentication on the login endpoint this fails: the session is
    authenticated, CSRF is enforced, and the token-less SPA login POST 403s with
    "CSRF Failed". `enforce_csrf_checks=True` makes that check real; `force_login`
    plants the session cookie that triggers it.
    """
    password = "applicantpass123"  # noqa: S105
    user = UserFactory(password=password)

    client = APIClient(enforce_csrf_checks=True)
    client.force_login(user)

    response = client.post(
        reverse("obtain_auth_token"),
        data={"username": user.email, "password": password},
        format="json",
    )

    assert response.status_code == HTTPStatus.OK
    assert "token" in response.data
