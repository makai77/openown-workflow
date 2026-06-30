from django.core.management.base import BaseCommand

from openown.users.models import User

SEED_USERS = [
    {
        "email": "applicant@example.com",
        "name": "Alice Applicant",
        "role": User.Role.APPLICANT,
        "password": "applicantpass123",
    },
    {
        "email": "reviewer@example.com",
        "name": "Bob Reviewer",
        "role": User.Role.REVIEWER,
        "password": "reviewerpass123",
        # Staff (but NO admin model permissions) only so the reviewer can open the
        # admin-gated API docs at /api/docs/ (SERVE_PERMISSIONS = IsAdminUser, i.e.
        # is_staff). Business access is governed by `role`, not by is_staff.
        "is_staff": True,
    },
]


class Command(BaseCommand):
    help = "Seed the database with one Applicant and one Reviewer demo user."

    def handle(self, *args, **options):
        for data in SEED_USERS:
            if User.objects.filter(email=data["email"]).exists():
                self.stdout.write(f"Already exists: {data['email']}")
                continue
            user = User.objects.create_user(
                email=data["email"],
                password=data["password"],
                name=data["name"],
                role=data["role"],
                is_staff=data.get("is_staff", False),
            )
            self.stdout.write(
                self.style.SUCCESS(f"Created {user.role} - {user.email}"),
            )
