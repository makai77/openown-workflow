from rest_framework.permissions import BasePermission


class IsApplicant(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_applicant,
        )


class IsReviewer(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.is_reviewer,
        )
