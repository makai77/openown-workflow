"""
Pydantic models for structured agent plans and reports.

Use AgentTaskPlan BEFORE an agent edits anything.
Use AgentChangeReport AFTER a slice is complete.
Use FinalSubmissionReport as the literal go/no-go check before submission.

These are agent-workflow helpers only — not DRF serializers, not production models.
"""

from enum import StrEnum

from pydantic import BaseModel
from pydantic import Field


class RiskLevel(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class AgentTaskPlan(BaseModel):
    task_summary: str
    files_to_read: list[str]
    files_to_edit: list[str]
    tests_to_add_or_update: list[str]
    commands_to_run: list[str]
    risks: list[str] = Field(default_factory=list)


class AgentChangeReport(BaseModel):
    files_changed: list[str]
    behavior_changed: list[str]
    tests_added_or_updated: list[str]
    commands_run: list[str]
    remaining_risks: list[str]
    risk_level: RiskLevel


class FinalSubmissionReport(BaseModel):
    ready: bool
    backend_tests_passed: bool
    frontend_build_passed: bool
    live_url_verified: bool
    applicant_credentials_verified: bool
    reviewer_credentials_verified: bool
    readme_complete: bool
    no_secrets_committed: bool
    known_issues: list[str] = Field(default_factory=list)
