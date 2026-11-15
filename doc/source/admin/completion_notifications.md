# Completion notifications

## Upgrade behavior

Saved email post-job actions no longer send mail. The workflow editor shows a notice for these actions and lets users remove them.

Users request completion notifications through the bell beside Run in the tool and workflow forms. "Notify me" applies only to that run. "Send email" saves a delivery preference for that notification category. Tool and workflow runs have separate categories.

Email is off by default for both categories. A saved email preference does not opt later runs into notifications. Users must select "Notify me" for each run.

For API submissions, use `send_notification` to request a completion notification.

The legacy API option `send_email_notification` still requests a completion notification. Delivery follows the user's saved preferences. The option does not force an email.

Tell users about these changes before the upgrade. Existing SMTP settings alone will not preserve completion emails.

## Configuration

Set `enable_notification_system: true` in the Galaxy configuration. Its default is `false`.

For workflow completion notifications, run the Celery worker that executes workflow completion hooks. For email delivery, also enable `enable_celery_tasks`. Run Celery Beat for fallback delivery and scheduled cleanup. Configure the broker and result backend as described in the [administrator guide for Celery](https://docs.galaxyproject.org/en/master/admin/production.html#use-celery-for-asynchronous-tasks).

Configure `smtp_server` and `email_from` for outgoing mail. Set `galaxy_infrastructure_url` to the public Galaxy URL so notification links use the correct address.

Tool completion notifications can appear in Galaxy without Celery. Email delivery requires Celery. Galaxy offers the email setting when `enable_celery_tasks` is `true`. This setting does not test the SMTP connection.

Apply the database migration before you start the upgraded application. It adds durable tool completion requests. Use the normal Galaxy upgrade procedure.

## Monitor placement

Galaxy starts background threads inside existing processes. This feature does not launch a separate monitor process.

The web process elected by Galaxy's database heartbeat runs one tool completion thread. Other web processes and job handlers do not poll tool completion requests.

The election uses the existing config-watcher role. If the elected process stops, another web process takes over after the heartbeat detects its departure. Pending requests remain in the database. Row locks and a conditional update protect delivery during an election change.

Each workflow-handler process runs its own workflow completion thread. That thread checks invocations assigned to its handler. With four workflow handlers and notifications enabled, Galaxy runs five completion threads in total.

## Polling and delivery delays

`workflow_completion_monitor_sleep` controls both completion monitors. Its default is 5 seconds.

Each monitor handles up to 100 requests per iteration. It advances through pending requests and then returns to the start. Large queues increase the delay before the monitor checks a request again.

For collection map-over, Galaxy waits until population finishes and every job reaches a settled state. It creates one summary for the map. Empty maps can also produce a summary.

Settled states include `ok`, `error`, `deleted`, `skipped`, `paused`, and `stopped`. A completion notification does not mean that every job succeeded.

Completion notifications queue a Celery task for email delivery as soon as Galaxy creates the notification. Email can arrive later than the notification in Galaxy if workers are busy.

If Galaxy cannot queue that task, the periodic dispatcher handles delivery. `dispatch_notifications_interval` defaults to 600 seconds and controls this fallback.

SSE delivers browser updates when enabled. Without SSE, the client polls for notifications. SSE does not replace either completion monitor or the email dispatcher.

## Default configuration

The notification system remains off by default in this release. The global flag also enables notifications for sharing and other categories. Some existing categories default to email on when Celery is available.

Enable the system after you configure delivery and review these defaults. Without Celery Beat, expired notifications do not receive the scheduled cleanup. Stored notifications and recipient associations can accumulate.

## User preferences

Users can turn a category off in their notification settings. The run form shows a warning when that category is off. The "Send email" option does not turn the category back on.

Saved delivery preferences also affect active runs. The email dispatcher reads the current preferences when it dispatches a notification.

## Troubleshooting

If the bell is absent, check `enable_notification_system` and confirm that the user has a tool or workflow run form open.

If a tool notification does not arrive, confirm that a web process runs and the database heartbeat elects a config watcher. Check if map population is complete and if jobs remain unsettled. Search the web process log for "Error polling tool completion notifications" or "Error delivering tool completion notification".

If a workflow notification does not arrive, check its workflow handler and Celery worker. Search the handler log for "Error queuing hook". Confirm that the user requested a notification for that invocation.

If a notification appears in Galaxy but email does not arrive, check the category preference, SMTP settings, and Celery worker. Search the worker log for "Error sending email notification". If the application logs "Could not queue the dispatch", also check Beat and allow for `dispatch_notifications_interval`.

For a smoke test, request a notification for a small collection map-over and enable email for tool runs. Confirm one summary in Galaxy and one email. Reopen the tool form and confirm that "Notify me" is off while "Send email" remains on.
