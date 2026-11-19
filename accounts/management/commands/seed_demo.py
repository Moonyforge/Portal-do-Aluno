from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from accounts.models import StudentProfile, User


class Command(BaseCommand):
    help = "Cria usuários de demonstração (somente com DEBUG=True)."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo só pode ser executado com DEBUG=True.")

        users = [
            ("secretaria", "secretaria@exemplo.com", "Secretaria@123", User.Role.STAFF, "Maria", "Secretaria", None),
            ("20260001", "ana.souza@exemplo.com", "Aluno@123456", User.Role.STUDENT, "Ana", "Souza", "20260001"),
            ("20260002", "bruno.lima@exemplo.com", "Aluno@123456", User.Role.STUDENT, "Bruno", "Lima", "20260002"),
        ]
        for username, email, password, role, first, last, reg in users:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email, "role": role,
                    "first_name": first, "last_name": last,
                },
            )
            if created:
                user.set_password(password)
                user.save()
            if reg:
                StudentProfile.objects.get_or_create(
                    user=user,
                    defaults={"registration_number": reg, "course": "Análise e Desenvolvimento de Sistemas"},
                )
            self.stdout.write(f"{'criado' if created else 'já existe'}: {username} ({role})")
