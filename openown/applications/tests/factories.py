from __future__ import annotations

import factory

from openown.users.models import User
from openown.users.tests.factories import UserFactory

from ..models import Application
from ..models import ApplicationAuditLog


class ApplicantFactory(UserFactory):
    email = factory.Sequence(lambda n: f"applicant{n}@example.com")
    role = User.Role.APPLICANT


class ReviewerFactory(UserFactory):
    email = factory.Sequence(lambda n: f"reviewer{n}@example.com")
    role = User.Role.REVIEWER


class ApplicationFactory(factory.django.DjangoModelFactory[Application]):
    owner = factory.SubFactory(ApplicantFactory)
    title = factory.Sequence(lambda n: f"Application {n}")
    category = Application.Category.GENERAL
    description = factory.Faker("paragraph")
    amount = "1000.00"
    status = Application.Status.DRAFT

    class Meta:
        model = Application


class ApplicationAuditLogFactory(
    factory.django.DjangoModelFactory[ApplicationAuditLog],
):
    application = factory.SubFactory(ApplicationFactory)
    actor = factory.SubFactory(ReviewerFactory)
    from_status = Application.Status.SUBMITTED
    to_status = Application.Status.UNDER_REVIEW
    comment = ""

    class Meta:
        model = ApplicationAuditLog
