"""
One-time backfill for applications that were created before an account was
required (see accounts.views.applicant_signup / admissions.views._get_draft).
Gives every one of them a parent account — username/email = the email they
already gave us, password = the phone number they already gave us — so the
school can tell each family to log in and continue or track their
application, instead of hunting for individual resume links.

Groups by email: siblings applied by the same parent under the same email
end up on ONE shared account (matching how a fresh signup already works).
Reuses an existing User/Guardian by email or phone instead of duplicating
one — safe to re-run; already-linked applications (created_by already set)
and rows with no usable email are left untouched and reported separately.

Usage:
    python manage.py backfill_applicant_accounts --dry-run   # preview only
    python manage.py backfill_applicant_accounts             # actually do it
"""

from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction
from django.db.models import Q


class Command(BaseCommand):
    help = 'Create parent accounts (password = their phone number) for every application that predates login.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Report what would happen without changing anything.')

    def handle(self, *args, **options):
        from accounts.models import User
        from admissions.models import Application
        from students.models import Guardian

        dry_run = options['dry_run']

        orphaned = Application.objects.filter(created_by__isnull=True).exclude(email='').order_by('created_at')
        groups = {}
        for app in orphaned:
            groups.setdefault(app.email.strip().lower(), []).append(app)

        report_rows = []
        skipped_no_phone = []
        skipped_errors = []
        new_accounts = 0
        reused_accounts = 0
        linked_applications = 0

        for email, apps in groups.items():
            # Most recently supplied non-blank value wins, in case an older
            # abandoned draft has a stale/blank phone but a later one for
            # the same email doesn't.
            phone = next((a.phone.strip() for a in reversed(apps) if a.phone.strip()), '')
            parent_name = next((a.parent_name.strip() for a in reversed(apps) if a.parent_name.strip()), '') or 'Parent'

            if not phone:
                skipped_no_phone.append((email, [a.application_number for a in apps]))
                continue

            try:
                with transaction.atomic():
                    guardian = Guardian.objects.filter(Q(email__iexact=email) | Q(phone=phone)).first()
                    user = User.objects.filter(email__iexact=email).first() or (guardian.user if guardian and guardian.user_id else None)

                    created_new = user is None
                    if dry_run:
                        if created_new:
                            new_accounts += 1
                        else:
                            reused_accounts += 1
                        linked_applications += len(apps)
                        report_rows.append((email, phone, parent_name, len(apps), 'NEW' if created_new else 'existing'))
                        continue

                    if user is None:
                        user = User.objects.create_user(username=email, email=email, password=phone, role='parent')
                        new_accounts += 1
                    else:
                        reused_accounts += 1

                    if guardian is None:
                        guardian = Guardian.objects.create(name=parent_name, phone=phone, email=email, user=user)
                    elif not guardian.user_id:
                        guardian.user = user
                        guardian.save(update_fields=['user'])

                    for app in apps:
                        app.created_by = user
                        app.save(update_fields=['created_by'])
                    linked_applications += len(apps)

                    report_rows.append((email, phone, parent_name, len(apps), 'NEW' if created_new else 'existing'))
            except IntegrityError as exc:
                skipped_errors.append((email, str(exc)))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== Accounts ===' if not dry_run else '=== DRY RUN — nothing changed ==='))
        self.stdout.write(f"{'Email':<35} {'Password (phone)':<18} {'Name':<25} {'Apps':<5} Account")
        for email, phone, name, count, status in report_rows:
            self.stdout.write(f"{email:<35} {phone:<18} {name:<25} {count:<5} {status}")

        if skipped_no_phone:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(f'Skipped {len(skipped_no_phone)} email(s) with no phone number on file (no password to set):'))
            for email, numbers in skipped_no_phone:
                self.stdout.write(f'  {email} — {", ".join(numbers)}')

        if skipped_errors:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR(f'{len(skipped_errors)} error(s):'))
            for email, err in skipped_errors:
                self.stdout.write(f'  {email} — {err}')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'{new_accounts} new account(s), {reused_accounts} existing account(s) reused, '
            f'{linked_applications} application(s) linked.'
        ))
