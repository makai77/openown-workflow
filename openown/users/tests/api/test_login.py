from http import HTTPStatus

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from openown.users.tests.factories import UserFactory


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
