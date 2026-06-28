from django.conf import settings
from django.db import models


class ApplicationQuerySet(models.QuerySet):
    def for_applicant(self, user):
        return self.filter(owner=user)

    def for_reviewer_queue(self):
        return self.exclude(status=Application.Status.DRAFT)

    def submitted_or_under_review(self):
        return self.filter(
            status__in=[
                Application.Status.SUBMITTED,
                Application.Status.UNDER_REVIEW,
            ],
        )

    def with_owner(self):
        return self.select_related("owner")

    def with_audit_trail(self):
        return self.prefetch_related(
            models.Prefetch(
                "audit_logs",
                queryset=ApplicationAuditLog.objects.select_related("actor").order_by(
                    "created_at",
                ),
            ),
        )


class Application(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        RETURNED = "RETURNED", "Returned for Changes"

    class Category(models.TextChoices):
        GENERAL = "GENERAL", "General"
        COMPLIANCE = "COMPLIANCE", "Compliance"
        FINANCE = "FINANCE", "Finance"
        OPERATIONS = "OPERATIONS", "Operations"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=30, choices=Category.choices)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ApplicationQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def is_editable_by_applicant(self) -> bool:
        return self.status == self.Status.DRAFT

    @property
    def is_reviewable(self) -> bool:
        return self.status in {self.Status.SUBMITTED, self.Status.UNDER_REVIEW}


class ApplicationAuditLog(models.Model):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="audit_logs",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="application_audit_logs",
    )
    from_status = models.CharField(max_length=30)
    to_status = models.CharField(max_length=30)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["application", "created_at"]),
            models.Index(fields=["actor", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.application} | {self.from_status} → {self.to_status}"
