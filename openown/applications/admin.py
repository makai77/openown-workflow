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


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ["title", "owner", "category", "status", "created_at"]
    list_filter = ["status", "category", "created_at"]
    search_fields = ["title", "description", "owner__email"]
    readonly_fields = ["submitted_at", "reviewed_at", "created_at", "updated_at"]
    list_select_related = ["owner"]
    inlines = [ApplicationAuditLogInline]
