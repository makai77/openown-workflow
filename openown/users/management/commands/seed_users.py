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
    },
]

# A Django-admin superuser for local inspection only. `role` governs business
# access; `is_staff`/`is_superuser` are kept separate, for the admin site.
SEED_ADMIN = {
    "email": "admin@example.com",
    "name": "Admin",
    "password": "adminpass123",
}


class Command(BaseCommand):
    help = (
        "Seed the database with one Applicant, one Reviewer, and a Django-admin "
        "superuser for local development."
    )

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
            )
            self.stdout.write(
                self.style.SUCCESS(f"Created {user.role} - {user.email}"),
            )

        if User.objects.filter(email=SEED_ADMIN["email"]).exists():
            self.stdout.write(f"Already exists: {SEED_ADMIN['email']}")
        else:
            admin = User.objects.create_superuser(
                email=SEED_ADMIN["email"],
                password=SEED_ADMIN["password"],
                name=SEED_ADMIN["name"],
            )
            self.stdout.write(
                self.style.SUCCESS(f"Created superuser - {admin.email}"),
            )
