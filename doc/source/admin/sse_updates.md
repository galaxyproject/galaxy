# Server-Sent Events (SSE) for real-time updates

Galaxy can push history changes, interactive-tool entry-point changes,
workflow invocation and job changes, and in-app notifications to connected
browsers via [Server-Sent Events][sse-mdn] instead of polling. The history
panel, interactive tool entry points and notifications then update over a
single long-lived HTTP connection per browser tab instead of the 3-second
history poll and 10-second entry-point poll, which reduces API load on busy
servers and gives users sub-second update latency.

This document covers the processes involved, the configuration, the metrics
to watch, and how to configure NGINX so the long-lived event connection is
not buffered or prematurely terminated. The event types, their payloads and
routing, and the subscription API are described for developers in
[Server-Sent Events: event types, routing and producers](../dev/sse_events.md).

[sse-mdn]: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events

## How it works

```
   ┌────────────────┐  LISTEN/NOTIFY     ┌──────────────────────┐   ┌─────────────────────────┐
   │  Postgres      │ ─────────────────► │ HistoryAuditMonitor  │   │ web workers, job        │
   │  history_audit │  (or audit poll    │ (one elected process) │   │ handlers, workflow      │
   │                │   on SQLite)       └──────────┬───────────┘   │ schedulers, Celery      │
   └────────────────┘                               │               │ (on each commit)        │
                                                    │ Kombu         └────────────┬────────────┘
                                                    ▼                            │ Kombu
                                     ┌─────────────────────────────┐             │
                                     │  AMQP control queue:        │ ◄───────────┘
                                     │  one control task per event │
                                     │  to every web worker        │
                                     └──────────────┬──────────────┘
                                                    ▼
                              ┌─────────────────────────────────────┐
                              │  Each gunicorn worker holds the     │
                              │  connections of its browser tabs    │
                              └──────────────┬──────────────────────┘
                                             │ HTTP chunked, /api/events/stream
                                             ▼
                              ┌─────────────────────────────────────┐
                              │  Browser EventSource                │
                              └─────────────────────────────────────┘
```

- **Web workers** hold the browsers' connections to `/api/events/stream`,
  in memory. Each worker needs its own control queue, see
  [What to monitor](#what-to-monitor).
- **History changes** are picked up by a `HistoryAuditMonitor` that watches
  the `history_audit` table via PostgreSQL `LISTEN/NOTIFY` (instant) or by
  polling it on SQLite. Only one process in the cluster runs it, picked by
  `DatabaseHeartbeat` leader election: a standalone `galaxy-sse-monitor`
  process if one runs, otherwise one webapp.
- **Workflow invocation, job, entry-point and notification changes** are sent
  by whichever Galaxy process commits them: web workers, job handlers,
  workflow schedulers or Celery workers. These processes need access to the
  AMQP broker configured by `amqp_internal_connection`.
- **Fan-out.** Every event travels as a control task over the internal AMQP
  connection to every web worker, which pushes it to the connections it
  holds and drops it otherwise. Job events add a message for each committed
  job state change, so expect noticeably more control-queue traffic on busy
  servers than with SSE updates off.
- **Delivery is best effort.** Events carry ids and states only, and
  browsers refetch the changed objects through the regular, access-controlled
  API. A failed dispatch is logged and leaves the browser to catch up on its
  next refetch; it never fails the change itself.

### Standalone monitor (recommended for production)

The `galaxy-sse-monitor` console script (installed by the `galaxy-app`
package) runs the `HistoryAuditMonitor` outside the webapp processes. This
is the recommended layout for production because:

- The webapp processes never compete with each other for the audit-monitor
  role on cold starts.
- Restarting the webapp tier doesn't briefly stall history updates while
  another worker is elected.
- The monitor needs only DB + AMQP access, so it can be sized
  independently and runs with a much smaller resident-set than a webapp.

A typical Gravity supervisor entry looks like the existing
`galaxy-celery-worker` block — point at the same `galaxy.yml` and run
`galaxy-sse-monitor` on its own. With the daemon present, the
`HistoryAuditMonitor` registered on the webapp side stays idle (the
heartbeat election picks the daemon) but is still wired up so it can take
over if the daemon goes away.

If `enable_sse_updates` is `false`, `galaxy-sse-monitor` will start, log a
warning, and idle — it does no work and produces no events.

## Configuration

There is a single admin-facing flag for SSE-driven updates:

```yaml
galaxy:
  enable_sse_updates: true
```

This controls **all** SSE-driven updates: history, entry-point, workflow
invocation and job changes, and notifications. When `false`:

- `HistoryAuditMonitor` is not registered, so the cluster does no
  `LISTEN/NOTIFY` or audit-table polling for history changes.
- No process sends invocation or job events.
- The browser falls back to its existing 3-second history poll and
  10-second entry-point poll.
- Notifications fall back to the existing 30-second polling against
  `/api/notifications/status`.

`enable_notification_system` is independent: it gates whether the
notification system is available at all (notification creation, delivery,
preferences, broadcasts). With `enable_notification_system: true`:

- `enable_sse_updates: true` → notifications arrive via SSE.
- `enable_sse_updates: false` → notifications are polled.

With `enable_notification_system: false` the entire notification system is
off — there is nothing to push or poll.

The polling-fallback knob for the history audit monitor stays available:

```yaml
galaxy:
  history_audit_monitor_poll_interval: 2  # seconds, SQLite / no-LISTEN only
```

This only matters when running on SQLite or in setups where PostgreSQL
`LISTEN/NOTIFY` is unavailable.

## What to monitor

In deployments with multiple independent Gunicorn masters on the same hostname, configure a
distinct `server_name` for each master as described in
[Scaling and Load Balancing](scaling.md#unique-server-names-for-independent-gunicorn-instances).
Each worker holds its own browser connections in memory and needs its own control queue.
Workers sharing a queue compete for messages instead of each receiving a copy, so SSE updates
can disappear even when the broker reports healthy consumers and empty queues.

When statsd is configured (via `statsd_host` and friends), the SSE
plumbing emits the following metrics. Capture these on the same dashboard
you use for Gunicorn worker health:

| Metric                                     | Type    | Source                | Meaning                                                      |
| ------------------------------------------ | ------- | --------------------- | ------------------------------------------------------------ |
| `galaxy.sse.connections.active` (tags: `kind`, `server_name`) | gauge | each web worker | Currently open SSE connections, split into `broadcast` (all, including anonymous) and `per_user` (bound to a specific user). |
| `galaxy.sse.connections.dropped`           | counter | `SSEConnectionManager` | A per-connection asyncio queue filled up; an event was lost. |
| `galaxy.sse.dispatch.count` (tag: `task`) | counter | `SSEEventDispatcher`  | Control-task fan-outs by event kind.                         |
| `galaxy.sse.dispatch.latency_ms` (tag: `task`) | timing | `SSEEventDispatcher`  | Wall time spent enqueueing the control task.                 |
| `galaxy.sse.dispatch.skipped_no_qw`        | counter | `SSEEventDispatcher`  | Producer tried to dispatch with no queue worker bound — events would have been dropped. |
| `galaxy.control_queue.depth` (tag: `queue_name`) | gauge | Celery beat | Pending message count per webapp/handler control queue. |
| `galaxy.worker_process.active` (tag: `app_type`) | gauge | Celery beat | Recently-active worker rows in the database, grouped by app type. |

All three are emitted as statsd **gauges** — point-in-time values, not timings —
so the datasource stores a single current value per series rather than the
mean/percentile aggregation statsd applies to timing metrics.

`galaxy.control_queue.depth` and `galaxy.worker_process.active` are sampled by
the `emit_queue_metrics_task` Celery beat task (cadence:
`queue_metrics_interval`).

`galaxy.sse.connections.active` is sampled differently: the
`SSEConnectionManager` is per-process state, so each **web worker** emits its
own counts (the Celery worker holds no connections and would only ever report
zero). Every worker tags its sample with its `server_name` so the per-worker
series don't collide — sum across `server_name` for a cluster total.

This gauge is **opt-in**: set `enable_sse_connection_metrics: true` (it is off
by default, so turning on statsd does not by itself start measuring SSE
connections). It then samples on the shared `queue_metrics_interval` cadence,
so that must be greater than 0.

Alerting recommendations:

- **`galaxy.sse.connections.dropped` > 0 sustained** indicates a slow or
  stuck client whose queue filled up. Occasional drops on a network blip
  are normal; a steady rate is a bug or a misconfigured proxy holding
  events back too long.
- **`galaxy.sse.dispatch.skipped_no_qw` > 0** means events are being lost
  because the producer process can't reach the AMQP bus. Check the
  `amqp_internal_connection` config and the AMQP broker health.
- **`galaxy.sse.dispatch.latency_ms` p95 climbing** points at an AMQP
  bottleneck (broker load, network) — events will land late.

In addition, watch the standard worker metrics. SSE connections are
long-lived (tens of minutes is common), but Galaxy runs Gunicorn with
`uvicorn.workers.UvicornWorker` (configured by Gravity by default), so
each worker process is async and can hold thousands of idle SSE
connections without blocking other requests. The practical concern on
busy servers is therefore memory and file-descriptor headroom, not
worker exhaustion: budget a few KB per connection plus one fd per
connection per worker, and raise `ulimit -n` accordingly.

## Configuring NGINX

The SSE endpoint is served at `/api/events/stream`. It is a normal
HTTP/1.1 chunked response, so it works through NGINX without any special
modules — but you must turn off response buffering and raise the
read/send timeouts, otherwise events will arrive in batched bursts (or
not at all until the connection times out).

Galaxy already sets `X-Accel-Buffering: no` on the response, which
disables NGINX's response buffering for that one endpoint without
affecting buffering on the rest of Galaxy. That alone is enough on most
setups. The block below adds the read/send timeouts and HTTP/1.1
upgrade-friendly headers explicitly so the connection survives long
idle periods between events:

```nginx
        # Long-lived Server-Sent Events stream.
        # Galaxy sends ``X-Accel-Buffering: no`` on the response, which
        # disables nginx response buffering just for this endpoint.
        # The keepalive comment fires every 30s so the read timeout
        # only needs to be a comfortable margin above that.
        location /api/events/stream {
            proxy_pass http://unix:/srv/galaxy/var/gunicorn.sock;
            proxy_set_header Host $http_host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            proxy_http_version 1.1;
            proxy_set_header Connection "";

            # Disable buffering and gzip explicitly. ``X-Accel-Buffering``
            # already does this, but pinning it here also covers setups
            # where a sub-filter strips upstream headers.
            proxy_buffering off;
            proxy_cache off;
            gzip off;

            # Keepalives fire every 30s; allow generous slack on top.
            proxy_read_timeout 1h;
            proxy_send_timeout 1h;
        }
```

Place this `location` block **above** the catch-all `location /` block in
your existing Galaxy `server {}` (see the [NGINX proxy guide](nginx.md)).
NGINX matches longest prefix first, so the order doesn't matter for
correctness, but keeping all the override blocks together at the top of
the server block makes the special-case handling easy to find.

If you serve Galaxy at a URL prefix (`/galaxy`), prefix the location too:

```nginx
        location /galaxy/api/events/stream {
            proxy_pass http://unix:/srv/galaxy/var/gunicorn.sock:/galaxy;
            # ...same body as above
        }
```

### Other proxies

If you front Galaxy with something other than NGINX, the same rules
apply: disable response buffering for `/api/events/stream`, allow the
connection to stay open for at least the `keepalive` interval (30 s by
default) plus a healthy margin, and pass the request through HTTP/1.1
without forcing `Connection: close`.

- **Apache `mod_proxy_http`**: add `ProxyPass` with
  `flushpackets=on flushwait=5` and bump `ProxyTimeout` to at least a
  few minutes. Avoid `mod_deflate` on this endpoint.
- **HAProxy**: the connection is a plain HTTP/1.1 chunked response and
  needs no special handling beyond `timeout server` and
  `timeout tunnel` raised above 30 s.
- **Cloudflare and other CDNs**: many CDNs buffer HTTP/1.1 chunked
  responses by default. Either bypass the CDN for `/api/events/stream`
  or follow the CDN's documented pattern for SSE streaming.

## Verifying the deployment

After enabling `enable_sse_updates`, three quick checks confirm the
stream is healthy end-to-end:

1. From the browser DevTools Network tab, open Galaxy and look for a
   `GET /api/events/stream` request that stays in the **pending** state
   with a constantly incrementing transferred-bytes count. The response
   `Content-Type` is `text/event-stream`.
2. Trigger a history change (run a tool, rename a dataset). The Network
   tab should show a `history_update` event in the EventStream view of
   that connection within a second or two, and the history panel
   refreshes without a polling round-trip.
3. On the server side, `galaxy.sse.dispatch.count` should be ticking up
   for each event kind your users exercise, and
   `galaxy.sse.connections.active` should reflect roughly one connection
   per open browser tab (summed across the reporting processes).

If the connection opens but no events arrive, check for proxy buffering (revisit the NGINX
section), a producer unable to dispatch control tasks (see `galaxy.sse.dispatch.skipped_no_qw`), and workers
sharing control queues because their server names collide.

Use the process manager and worker startup logs to verify that only one live Galaxy worker
process uses each `server_name` on a given hostname. For Gunicorn, check the final name including
the worker ID, such as `web_0.1`. This requirement applies regardless of the control-queue
transport. See [unique server names](scaling.md#unique-server-names-for-independent-gunicorn-instances)
for configuration guidance.
