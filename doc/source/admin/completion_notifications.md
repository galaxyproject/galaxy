# Completion notifications

## Upgrade behavior

Saved email post-job actions no longer send mail. The workflow editor shows a notice for these actions and lets users remove them.

Users request a completion message through the bell beside Run in the tool and workflow forms. The choice applies only to that run. Collection map-over produces one summary after the whole map settles.

Galaxy supports two delivery modes:

| Configuration | Run form | Delivery |
| --- | --- | --- |
| Notifications disabled, SMTP configured | "Email me when finished" | One email for the requested run. No Celery required. |
| Notifications enabled | "Notify me", plus saved "Send email" preference | In-app notification, with optional email through Celery. |
| Notifications disabled, no SMTP | No bell | Completion messages unavailable. |

Existing SMTP settings support the email-only mode. Administrators do not need to enable the notification system to keep per-run completion emails. Users must request them through the run form or API. Legacy workflow email actions remain retired.

For tool API submissions, use `send_notification`. The legacy option `send_email_notification` is an alias. Workflow API submissions use `on_complete: [{"send_notification": {}}]`.

## Configuration

Configure `smtp_server` and `email_from` for outgoing mail. Set `galaxy_infrastructure_url` to the public Galaxy URL so emails link to the correct address.

With `enable_notification_system: false`, those settings are sufficient for completion emails. Galaxy records each requested email in the database. A separate thread sends it through SMTP. It does not create an in-app notification or enable other notification categories.

To offer in-app notifications, set `enable_notification_system: true`. Workflow notification hooks require a Celery worker. For email delivery through the notification system, also enable `enable_celery_tasks`. Run Celery Beat for fallback delivery and scheduled cleanup. See the [administrator guide for Celery](https://docs.galaxyproject.org/en/master/admin/production.html#use-celery-for-asynchronous-tasks).

Tool notifications can appear in Galaxy without Celery. When the notification system is enabled, its email channel requires Celery. The run form offers that channel when `enable_celery_tasks` is true. This setting does not test the SMTP connection.

Apply the database migrations through the normal Galaxy upgrade procedure. They add durable tool completion requests and fields for email-only delivery leases.

## Monitor placement and delays

Galaxy starts background threads inside existing processes. This feature does not launch a separate process.

When notifications or SMTP are configured, the web process elected by the database heartbeat runs one tool completion thread. When SMTP is configured, that process also runs one email dispatcher thread. SMTP calls cannot block either completion monitor. Other web processes and job handlers do not poll these global queues.

The election uses the existing config-watcher role. If the elected process stops, another web process takes over after the heartbeat detects its departure.

Each workflow-handler process runs its own workflow completion thread and checks its assigned invocations. With four workflow handlers and SMTP configured, Galaxy runs four workflow completion threads, one tool completion thread, and one email dispatcher thread.

`workflow_completion_monitor_sleep` controls these threads. Its default is 5 seconds. Each handles up to 100 requests per iteration. The threads advance through pending requests and then return to the start. Large queues increase the delay before the monitor checks a request again.

For collection map-over, Galaxy waits until population finishes and every job reaches a settled state. Empty maps can also produce a summary. Settled states include `ok`, `error`, `deleted`, `skipped`, `paused`, and `stopped`. A completion message does not mean that every job succeeded.

## Email delivery

In email-only mode, Galaxy records the email request and completion marker in one transaction. The dispatcher claims each email for five minutes and releases its database connection before it contacts SMTP. Socket operations have a 30-second timeout. Galaxy retries failed sends after the lease expires, even after a restart. The dispatcher removes successful sends from the queue. It also removes expired requests without sending them.

SMTP cannot guarantee exactly-once delivery. If the server accepts an email and Galaxy stops before it records success, a retry can send a duplicate.

With the notification system enabled, completion notifications queue a Celery task for email delivery immediately. If Galaxy cannot queue the task, the periodic dispatcher handles it. `dispatch_notifications_interval` controls this fallback and defaults to 600 seconds.

SSE delivers browser updates when enabled. Otherwise, the client polls for notifications. SSE does not replace completion checks or email delivery.

## Defaults and preferences

The notification system remains off by default. The global flag also enables sharing and other categories, some of which default to email on. Review those defaults before you enable it. Without Celery Beat, expired in-app notifications and recipient associations can accumulate.

With notifications enabled, email is off by default for tool and workflow completion. The two categories have separate delivery preferences. "Send email" saves a preference, but does not opt later runs into notifications. Saved preferences also affect active runs.

Users can mute a category in their account settings. The run form warns about a muted category. The "Send email" option does not unmute it.

Email-only mode has no saved delivery preference. The per-run checkbox explicitly requests an email, even if the user previously muted an in-app category.

## Troubleshooting

If the bell is absent, check the notification and SMTP configuration.

If a tool message does not arrive, confirm that a web process runs and the heartbeat elects a config watcher. Check if map population is complete and any jobs remain unsettled. Search the web process log for "Error polling tool completion notifications" or "Error delivering tool completion notification".

For email-only delivery failures, search the elected web process log for "Could not send completion email". Check SMTP settings and allow five minutes for a retry. A queued email remains eligible if you later enable the notification system.

If a workflow message does not arrive, check its workflow handler. With notifications enabled, also check the Celery worker and search for "Error queuing hook". Confirm that the user requested a message for that invocation.

If an in-app notification arrives without email, check the category preference, SMTP settings, and Celery worker. Search for "Error sending notification". If Galaxy logs "Could not queue the dispatch", check Beat and allow for `dispatch_notifications_interval`.

For an email-only smoke test, request an email for a small collection map-over. Confirm one summary email, then reopen the run form and confirm the checkbox is off.
