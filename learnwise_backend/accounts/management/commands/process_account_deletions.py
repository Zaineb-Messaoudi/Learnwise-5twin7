from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import AccountDeletionRequest


class Command(BaseCommand):
    help = (
        'Permanently delete accounts whose deletion request was confirmed and whose '
        '30-day grace period has expired. Schedule this daily (cron / Task Scheduler).'
    )

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='List accounts without deleting them.')

    def handle(self, *args, **options):
        due = AccountDeletionRequest.objects.filter(
            status='confirmed',
            scheduled_deletion_at__isnull=False,
            scheduled_deletion_at__lte=timezone.now(),
        ).select_related('user')

        count = 0
        for request in due:
            user = request.user
            if user.is_superuser:
                self.stdout.write(self.style.WARNING(f'Skipping superuser {user.email}'))
                continue
            if options['dry_run']:
                self.stdout.write(f'[dry-run] would delete {user.email}')
                continue
            email = user.email
            # Deleting the user cascades to sessions, security events, face profile, etc.
            user.delete()
            count += 1
            self.stdout.write(self.style.SUCCESS(f'Deleted account {email}'))

        self.stdout.write(f'{count} account(s) deleted.')
