# Server-Sent Events: event types, routing and producers

With `enable_sse_updates` on, Galaxy pushes change notifications to browsers over a single
[Server-Sent Events][sse-mdn] stream. This page describes the events for client and Galaxy
developers: what each event carries, who receives it, and how the server produces it. Deployment,
configuration, monitoring and proxy setup are covered in the admin guide,
[Server-Sent Events (SSE) for real-time updates](../admin/sse_updates.md).

[sse-mdn]: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events

## The stream

A client opens one `EventSource` against `GET /api/events/stream` and receives every event type
on it. The first frame on every connection is a `ready` event, sent once the server has registered
the connection; every event dispatched after that reaches it. A keepalive comment follows every 30
seconds of silence.

The endpoint accepts connections even when `enable_sse_updates` is off, but then no producer sends
change events. Clients therefore choose between the stream and polling by the `enable_sse_updates`
value in `/api/configuration`, not by whether the connection opens.

Events are wake-up signals: they carry ids and states, and the client refetches the full objects
through the regular, access-controlled API. A client should also refetch after reconnecting, since
events sent while it was disconnected are lost (only `notification_status` is replayed, see below).

## Event types

| Event | Data | Sent when |
| --- | --- | --- |
| `history_update` | `{"history_ids": [<id>, ...]}` | A history, or a dataset or collection in it, changed. |
| `entry_point_update` | `{}` | One of the user's interactive tool entry points was configured. Refetch `/api/entry_points`. |
| `invocation_update` | `{"invocations": [{"id": <id>, "state": <state>}, ...]}` | A workflow invocation's state changed, one of its steps was added or changed state, or a message was added to it. `state` is the invocation's current state. |
| `job_update` | `{"jobs": [{"id": <id>, "state": <state>}, ...]}` or `{"resync": true}` | A job's state changed. `state` is the job's state at commit. |
| `notification_update` | A `NotificationResponse` | A notification was sent to the user. |
| `broadcast_update` | A `BroadcastNotificationResponse` | A broadcast was created. |
| `notification_status` | A `NotificationStatusSummary` | On reconnect with `Last-Event-ID`, everything since that event. |

All ids are encoded. An `invocation_update` for an invocation whose state is unchanged means its
steps or messages changed. A `job_update` with `{"resync": true}` replaces the individual entries
when one transaction changed more than 500 jobs of the recipient (for example a tool mapped over a
large collection): the client refetches all jobs it shows.

## Routing

Events are routed to the users and anonymous browser sessions allowed to see them:

- `history_update` goes to the owner of the history, or for an anonymous history to its browser
  session. `invocation_update` goes to the owner of the invocation's history.
- `job_update` goes to the job's user. An anonymous job's events go to the owner of its history
  once a user has logged in and taken over that history, and otherwise to its browser session.
- `entry_point_update` and `notification_update` go to their user, `broadcast_update` to everyone.

In addition, `history_update`, `invocation_update` and `job_update` reach the **viewers** of a
history: users or sessions watching a history they don't own, such as a published history or one
shared with them. A client subscribes and unsubscribes with:

```
POST   /api/events/history-subscriptions  {"history_ids": [<id>, ...]}
DELETE /api/events/history-subscriptions  {"history_ids": [<id>, ...]}
```

Both return 204. Only histories the requester can access are subscribed (owned, shared with them,
importable or published, or their anonymous current history); other and malformed ids are skipped.
Access is checked when subscribing: a viewer keeps receiving events for a history made private
later until it unsubscribes or disconnects. Every web worker holds the subscriptions of the users
and sessions connected to it, and drops them when the last connection of that user or session on
the worker closes, so clients re-send them after reconnecting. A viewer receives only the entries for the histories it watches,
and an owner subscribed to their own history receives each event once.

## Producers

Every event travels as a Kombu control task to all web workers (`galaxy.queue_worker`), and each
worker pushes it to the connections it holds. `SSEEventDispatcher` (`galaxy.managers.sse_dispatch`)
sends these tasks from any Galaxy process with an AMQP connection.

- `history_update` comes from `HistoryAuditMonitor`, which follows the `history_audit` table that
  database triggers fill (PostgreSQL `LISTEN/NOTIFY`, or polling on SQLite).
- `invocation_update` and `job_update` come from `ChangeEventPublisher`
  (`galaxy.managers.change_events`). It listens on the app's SQLAlchemy sessionmaker, collects the
  invocations and jobs changed in a transaction (`galaxy.model.pending_changes`) and sends them
  when the root transaction commits, in whichever process committed it. Rolled back transactions
  and savepoints send nothing.
- `entry_point_update` and the notification events are sent explicitly by the code that makes the
  change.

`ChangeEventPublisher` sees changes made through the ORM unit of work: state assignments on
invocations and jobs, new invocation steps and messages, and the `JobStateHistory` row that
`Job.set_state` adds. A bulk `UPDATE` that changes invocation or job states bypasses the unit of
work and must record its changes itself with `record_invocation_change` or `record_job_change`, as
`WorkflowInvocation.set_state` and `WorkflowInvocation.cancel_invocation_steps` do. Otherwise it
sends no event.

## Tests

`galaxy_test.base.sse` provides `SSELineListener`, a stream client for integration tests, and
`SSEWaiter`, which backs the populators' waits (`wait_for_job`, `wait_for_history`,
`wait_for_invocation`, ...). Against a server with `enable_sse_updates`, these waits re-check only
when a matching event arrives, so a missing event makes them time out; for a history the current
user doesn't own, they subscribe as a viewer for the wait. Against other servers they poll.
`SSEIntegrationTestCase` in `galaxy_test.driver.integration_util` starts a server with SSE updates
enabled.
