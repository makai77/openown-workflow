from http import HTTPStatus

import pytest
from django.urls import reverse


def test_api_docs_accessible_by_admin(admin_client):
    url = reverse("api-docs")
    response = admin_client.get(url)
    assert response.status_code == HTTPStatus.OK


@pytest.mark.django_db
def test_api_docs_not_accessible_by_anonymous_users(client):
    url = reverse("api-docs")
    response = client.get(url)
    # Anonymous access to a protected endpoint is 401 per the error contract
    # (§6.4: not_authenticated). The project exception handler forces this rather
    # than letting DRF downgrade it to 403 when SessionAuthentication sets no
    # WWW-Authenticate header.
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_api_schema_generated_successfully(admin_client):
    url = reverse("api-schema")
    response = admin_client.get(url)
    assert response.status_code == HTTPStatus.OK
