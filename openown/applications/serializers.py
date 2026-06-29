from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Application
from .models import ApplicationAuditLog
from .services.workflow import REVIEWER_ACTION_KEYS
from .services.workflow import available_actions


class ApplicationCreateSerializer(serializers.ModelSerializer[Application]):
    class Meta:
        model = Application
        fields = ["id", "title", "category", "description", "amount", "status"]
        read_only_fields = ["id", "status"]


class ApplicationUpdateSerializer(serializers.ModelSerializer[Application]):
    class Meta:
        model = Application
        fields = ["title", "category", "description", "amount"]

    def validate(self, attrs):
        # Source of truth for "may the applicant edit this?" is the model property,
        # not a literal status check. It allows DRAFT and RETURNED (a returned
        # application goes back to the owner to revise before re-submitting). This
        # deliberately broadens Playbook §6.1's `status == DRAFT` check to stay
        # consistent with the committed `is_editable_by_applicant` property.
        if self.instance and not self.instance.is_editable_by_applicant:
            raise serializers.ValidationError(
                {"status": "Only draft or returned applications can be edited."},
            )
        return attrs


class ApplicationAuditLogSerializer(serializers.ModelSerializer[ApplicationAuditLog]):
    actor_name = serializers.CharField(source="actor.name", read_only=True)
    actor_email = serializers.EmailField(source="actor.email", read_only=True)

    class Meta:
        model = ApplicationAuditLog
        fields = [
            "id",
            "actor_name",
            "actor_email",
            "from_status",
            "to_status",
            "comment",
            "created_at",
        ]


class ApplicationListSerializer(serializers.ModelSerializer[Application]):
    # Used for every *list* response (applicant's own list, reviewer queue).
    # Deliberately omits audit_logs: a list view never needs the full trail, and
    # nesting it here would re-introduce the N+1 the queryset works to avoid.
    owner_email = serializers.EmailField(source="owner.email", read_only=True)

    class Meta:
        model = Application
        fields = [
            "id",
            "owner_email",
            "title",
            "category",
            "amount",
            "status",
            "submitted_at",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ApplicationDetailSerializer(serializers.ModelSerializer[Application]):
    # Used only for single-object reads and transition responses, where the caller
    # genuinely needs the trail. The queryset feeding this must apply
    # .with_owner().with_audit_trail() so this stays a fixed-query read.
    audit_logs = ApplicationAuditLogSerializer(many=True, read_only=True)
    owner_email = serializers.EmailField(source="owner.email", read_only=True)
    available_actions = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = [
            "id",
            "owner",
            "owner_email",
            "title",
            "category",
            "description",
            "amount",
            "status",
            "submitted_at",
            "reviewed_at",
            "created_at",
            "updated_at",
            "audit_logs",
            "available_actions",
        ]
        read_only_fields = fields

    @extend_schema_field(
        serializers.ListField(
            child=serializers.ChoiceField(choices=list(REVIEWER_ACTION_KEYS)),
        ),
    )
    def get_available_actions(self, obj: Application) -> list[str]:
        # The reviewer-action keys the current actor may invoke on this object,
        # straight from the workflow service — the frontend renders these and
        # encodes zero rules of its own. Pure: it reads only the already-loaded
        # object and request.user, so it adds no query. Absent request (e.g.
        # schema introspection) → empty, never an error.
        request = self.context.get("request")
        if request is None:
            return []
        return available_actions(application=obj, actor=request.user)


class TransitionCommentSerializer(serializers.Serializer):
    comment = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
    )
