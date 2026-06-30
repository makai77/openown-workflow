from io import StringIO

import pytest
from django.core.management import call_command

from openown.users.models import User


@pytest.mark.django_db
def test_seed_users_creates_applicant_and_reviewer_idempotently():
    output = StringIO()

    call_command("seed_users", stdout=output)
    call_command("seed_users", stdout=output)

    applicant = User.objects.get(email="applicant@example.com")
    reviewer = User.objects.get(email="reviewer@example.com")

    assert applicant.role == User.Role.APPLICANT
    assert applicant.check_password("applicantpass123")
    assert reviewer.role == User.Role.REVIEWER
    assert reviewer.check_password("reviewerpass123")
    assert User.objects.filter(email="applicant@example.com").count() == 1
    assert User.objects.filter(email="reviewer@example.com").count() == 1
    assert not User.objects.filter(is_superuser=True).exists()
