from __future__ import annotations

import pytest

from openown.users.models import User
from openown.users.tests.factories import UserFactory


def test_user_get_absolute_url(user: User):
    assert user.get_absolute_url() == f"/users/{user.pk}/"


@pytest.mark.django_db
def test_user_is_applicant_true():
    user = UserFactory.create(role=User.Role.APPLICANT)
    assert user.is_applicant is True
    assert user.is_reviewer is False


@pytest.mark.django_db
def test_user_is_reviewer_true():
    user = UserFactory.create(role=User.Role.REVIEWER)
    assert user.is_reviewer is True
    assert user.is_applicant is False


@pytest.mark.django_db
def test_user_role_defaults_to_applicant():
    user = UserFactory.create()
    assert user.role == User.Role.APPLICANT
    assert user.is_applicant is True
