"""OpenAPI documentation helpers (drf-spectacular only — no runtime behavior).

These serializers exist solely so the generated schema documents our real error
envelope — the `{"error": {code, message, details}}` shape produced by
``views.workflow_error_response`` and ``exception_handler.api_exception_handler``
(Playbook §6.4) — instead of a generic, untyped 400/403 body. They are never used
to validate or render an actual response.
"""

from rest_framework import serializers


class ErrorDetailSerializer(serializers.Serializer):
    code = serializers.CharField(
        help_text="Machine-readable error code, e.g. invalid_transition.",
    )
    message = serializers.CharField(
        help_text="Human-readable summary of what went wrong.",
    )
    details = serializers.DictField(
        required=False,
        help_text="Optional field-level detail; empty object for workflow errors.",
    )


class ErrorResponseSerializer(serializers.Serializer):
    error = ErrorDetailSerializer()
