# Account Deletion Processor - Scheduling Guide

The `process_account_deletions` management command permanently deletes accounts whose
30-day grace period has expired. It must be run **daily** to enforce the deletion policy.

## Option 1: systemd Timer (Recommended for systemd-based systems)

Files provided:
- `learnwise-process-deletions.service` - Service definition
- `learnwise-process-deletions.timer` - Daily timer

### Installation

```bash
# Copy files to systemd directory
sudo cp accounts/management/commands/learnwise-process-deletions.service /etc/systemd/system/
sudo cp accounts/management/commands/learnwise-process-deletions.timer /etc/systemd/system/

# Reload systemd and enable timer
sudo systemctl daemon-reload
sudo systemctl enable --now learnwise-process-deletions.timer

# Verify
systemctl list-timers | grep learnwise
journalctl -u learnwise-process-deletions.service -f
```

## Option 2: Cron (Universal)

Add to crontab (run as the Django application user):

```bash
# Edit crontab
crontab -e

# Add this line to run daily at 3:30 AM
30 3 * * * /path/to/venv/bin/python /path/to/learnwise_backend/manage.py process_account_deletions >> /var/log/learnwise/process_deletions.log 2>&1
```

### With Django settings module:

```bash
30 3 * * * DJANGO_SETTINGS_MODULE=learnwise_backend.settings /path/to/venv/bin/python /path/to/learnwise_backend/manage.py process_account_deletions >> /var/log/learnwise/process_deletions.log 2>&1
```

## Option 3: Manual / One-off

```bash
# Dry run to see what would be deleted
python manage.py process_account_deletions --dry-run

# Actually process deletions
python manage.py process_account_deletions
```

## Verification

The command outputs the number of deleted accounts:
```
$ python manage.py process_account_deletions
Deleted account user@example.com
1 account(s) deleted.
```

Or with dry-run:
```
$ python manage.py process_account_deletions --dry-run
[dry-run] would delete user@example.com
1 account(s) deleted.
```

## Important Notes

1. **Run daily** - The 30-day grace period relies on daily execution
2. **Run as application user** - Same user that runs the Django app (for file permissions)
3. **Monitor logs** - Check logs regularly to ensure it's running
3. **Superusers are skipped** - The command never deletes superuser accounts
4. **Dry-run first** - Test with `--dry-run` before enabling the timer/cron

## Log Location

- systemd: `journalctl -u learnwise-process-deletions.service`
- cron: `/var/log/learnwise/process_deletions.log` (ensure directory exists)

## Dependencies

- Django management command: `accounts.management.commands.process_account_deletions`
- Requires Django settings module to be configured