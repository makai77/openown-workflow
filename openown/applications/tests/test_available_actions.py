"""
available_actions() matrix — the read-only authority for "what can this actor do
to this application right now". Two things are proven here:

  1. Exact set per status and role (a reviewer sees the legal actions; an applicant
     or anonymous user sees nothing).
  2. Consistency with the transition functions: every action available_actions()
     reports as available actually succeeds, and every one it withholds is in fact
     rejected by the corresponding transition function. The two can never drift
     because they read the same predicates.

The set tests use unbuilt/unsaved factory instances (no @pytest.mark.django_db) to
make the "pure, no DB" contract explicit. The consistency test invokes the real
transition functions, so it touches the database.
"""

import pytest
from django.contrib.auth.models import AnonymousUser

from ..models import Application
from ..services import approve_application
from ..services import reject_application
from ..services import return_application
from ..services import start_review_application
from ..services.exceptions import InvalidTransition
from ..services.workflow import available_actions
from .factories import ApplicantFactory
from .factories import ApplicationFactory
from .factories import ReviewerFactory

S = Application.Status

# The complete, ordered vocabulary and the exact subset legal from each status.
REVIEWER_EXPECTED: dict[str, list[str]] = {
    S.DRAFT: [],
    S.SUBMITTED: ["start_review", "approve", "reject", "return"],
    S.UNDER_REVIEW: ["approve", "reject", "return"],
    S.APPROVED: [],
    S.REJECTED: [],
    S.RETURNED: [],
}

# How to actually invoke each action's transition function, used by the
# consistency test. reject/return get a non-blank comment so that *status* is the
# only thing that can reject them.
ACTION_FNS = {
    "start_review": lambda app, actor: start_review_application(
        application=app, actor=actor,
    ),
    "approve": lambda app, actor: approve_application(application=app, actor=actor),
    "reject": lambda app, actor: reject_application(
        application=app, actor=actor, comment="needs detail",
    ),
    "return": lambda app, actor: return_application(
        application=app, actor=actor, comment="please revise",
    ),
}


@pytest.mark.parametrize(("status", "expected"), REVIEWER_EXPECTED.items())
def test_reviewer_available_actions_per_status(status, expected):
    reviewer = ReviewerFactory.build()
    application = ApplicationFactory.build(status=status)

    assert available_actions(application=application, actor=reviewer) == expected


@pytest.mark.parametrize("status", list(REVIEWER_EXPECTED))
def test_applicant_never_has_reviewer_actions(status):
    applicant = ApplicantFactory.build()
    application = ApplicationFactory.build(status=status)

    assert available_actions(application=application, actor=applicant) == []


@pytest.mark.parametrize("status", list(REVIEWER_EXPECTED))
def test_anonymous_user_has_no_actions(status):
    application = ApplicationFactory.build(status=status)

    assert available_actions(application=application, actor=AnonymousUser()) == []


@pytest.mark.django_db
@pytest.mark.parametrize("status", list(REVIEWER_EXPECTED))
def test_available_actions_agree_with_transition_functions(status):
    # For every status: the actions available_actions() reports must succeed, and
    # the ones it withholds must be rejected by their transition function. Each
    # action runs against a fresh application so one transition doesn't perturb
    # the next.
    reviewer = ReviewerFactory.create()
    available = available_actions(
        application=ApplicationFactory.build(status=status),
        actor=reviewer,
    )

    for action, fn in ACTION_FNS.items():
        application = ApplicationFactory.create(status=status)
        if action in available:
            fn(application, reviewer)  # must not raise
            application.refresh_from_db()
            assert application.status != status
        else:
            with pytest.raises(InvalidTransition):
                fn(application, reviewer)
            application.refresh_from_db()
            assert application.status == status
            assert application.audit_logs.count() == 0
