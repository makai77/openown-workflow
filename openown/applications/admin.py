from django.contrib import admin

from .models import Application
from .models import ApplicationAuditLog


class ApplicationAuditLogInline(admin.TabularInline):
    model = ApplicationAuditLog
    extra = 0
    can_delete = False
    readonly_fields = ["actor", "from_status", "to_status", "comment", "created_at"]

    def get_queryset(self, request):
        # The inline renders `actor` on every row; resolve the FK in one JOIN
        # instead of a query per audit entry on the detail page.
        return super().get_queryset(request).select_related("actor")

    def has_add_permission(self, request, obj=None):
        # The audit trail is authored solely by the workflow service. The admin
        # must never be able to fabricate a row that no transition produced.
        return False


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ["title", "owner", "category", "status", "created_at"]
    list_filter = ["status", "category", "created_at"]
    search_fields = ["title", "description", "owner__email"]
    # `status`, `owner`, and the timestamps are backend-assigned and may change
    # only through applications/services/workflow.py. The admin is an
    # inspection-only window onto the data: editing `status` here would bypass
    # the transition guards and leave the audit trail without a matching row,
    # so it is read-only. Descriptive fields stay editable for data correction.
    readonly_fields = [
        "owner",
        "status",
        "submitted_at",
        "reviewed_at",
        "created_at",
        "updated_at",
    ]
    list_select_related = ["owner"]
    inlines = [ApplicationAuditLogInline]
