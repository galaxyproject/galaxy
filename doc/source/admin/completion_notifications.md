# Completion notifications

## Upgrade behavior

Saved workflow email post-job actions no longer send mail. The workflow editor shows a notice and lets users remove them.

Users request a completion message through the bell beside Run in the tool and workflow forms. The choice applies only to that run. A collection map produces one summary for the whole run.

Existing SMTP settings support completion emails without enabling the notification system or Celery.

## Configuration

For email-only delivery, configure `smtp_server` and `email_from`. Set `galaxy_infrastructure_url` to the public Galaxy URL so emails link to the correct address. Leave `enable_notification_system: false`, its default. The bell then offers "Email me when finished".

To offer in-app notifications, set `enable_notification_system: true`. Workflow notifications require a Celery worker. For email delivery, also set `enable_celery_tasks: true` and configure SMTP. Run Celery Beat for fallback delivery and notification cleanup. See the [administrator guide for Celery](https://docs.galaxyproject.org/en/master/admin/production.html#use-celery-for-asynchronous-tasks).

With notifications enabled, users select "Notify me" for each run. "Send email" saves a delivery preference, which defaults to off for tool and workflow completion. Enabling the notification system also enables other notification categories, some of which default to email on.

## Troubleshooting

If the bell is absent, check the notification and SMTP configuration.

If a completion email does not arrive, confirm that the user requested it and the run has finished. Check SMTP settings and application logs. With notifications enabled, also check the user's delivery preferences and that the Celery worker and Beat are running.
