from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def _code_for(exc) -> str:
    # Map exception types onto the project error contract (Playbook §6.4). DRF
    # normalises Http404 -> NotFound and Django's PermissionDenied -> 403 inside
    # its handler, but it passes us the *original* exc, so we recognise those
    # forms here too. WorkflowError never reaches here — the ViewSets catch it and
    # respond via workflow_error_response — so this only covers framework errors.
    if isinstance(exc, (exceptions.NotAuthenticated, exceptions.AuthenticationFailed)):
        return "not_authenticated"
    if isinstance(exc, (exceptions.PermissionDenied, DjangoPermissionDenied)):
        return "permission_denied"
    if isinstance(exc, (exceptions.NotFound, Http404)):
        return "not_found"
    if isinstance(exc, exceptions.ValidationError):
        return "validation_error"
    return getattr(exc, "default_code", "error")


def api_exception_handler(exc, context):
    """Wrap every DRF error in the {"error": {code, message, details}} contract.

    DRF's default body is `{"detail": ...}`; the rubric requires a single
    structured envelope and the correct status per §6.4. We also force
    NotAuthenticated to 401: DRF otherwise downgrades anonymous requests to 403
    when the first authenticator (SessionAuthentication) sets no WWW-Authenticate
    header, but the contract says an anonymous protected action is 401.
    """
    response = drf_exception_handler(exc, context)
    if response is None:
        # Not a DRF-handled exception — let it surface as a 500 (and never as a
        # 200 with an error body). We do not leak the stack trace in the body.
        return None

    code = _code_for(exc)
    status_code = response.status_code
    if isinstance(exc, exceptions.NotAuthenticated):
        status_code = 401

    if isinstance(exc, exceptions.ValidationError):
        # Field-level errors belong in details; the message is a fixed summary.
        message = "Validation failed."
        details = response.data
    else:
        detail = getattr(exc, "detail", response.data)
        message = str(detail)
        details = {}

    return Response(
        {"error": {"code": code, "message": message, "details": details}},
        status=status_code,
        headers={
            key: value
            for key, value in response.headers.items()
            if key.lower() == "www-authenticate"
        },
    )
