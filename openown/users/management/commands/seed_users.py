from django.core.management.base import BaseCommand

from openown.users.models import User

SEED_USERS = [
    {
        "email": "applicant@example.com",
        "name": "Alice Applicant",
        "role": User.Role.APPLICANT,
        "password": "applicantpass123",
        "is_staff": False,
    },
    {
        "email": "reviewer@example.com",
        "name": "Bob Reviewer",
        "role": User.Role.REVIEWER,
        "password": "reviewerpass123",
        "is_staff": False,
    },
]


class Command(BaseCommand):
    help = (
        "Seed the database with one Applicant and one Reviewer for local development."
    )

    def handle(self, *args, **options):
        for data in SEED_USERS:
            password = data.pop("password")
            user, created = User.objects.get_or_create(
                email=data["email"],
                defaults=data,
            )
            if created:
                user.set_password(password)
                user.save(update_fields=["password"])
                self.stdout.write(
                    self.style.SUCCESS(f"Created {user.role} — {user.email}"),
                )
            else:
                self.stdout.write(f"Already exists: {user.email}")
