# Server-Sent Events (SSE) for real-time updates

Galaxy can push history changes, interactive-tool entry-point changes, and
in-app notifications to connected browsers via [Server-Sent Events][sse-mdn]
instead of polling. This replaces the legacy 3-second history poll and
10-second entry-point poll with a single long-lived HTTP connection per
browser tab, dramatically reducing API load on busy servers and giving users
sub-second update latency.

This document describes the architecture, the configuration knobs, the
metrics admins should watch, and how to configure NGINX so the long-lived
event connection is not buffered or prematurely terminated.

[sse-mdn]: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events

## How it works

A high-level view of the moving parts on the server:

```
   ┌────────────────┐  LISTEN/NOTIFY     ┌──────────────────────┐
   │  Postgres      │ ─────────────────► │ HistoryAuditMonitor  │
   │  history_audit │  (or audit poll    │ (one elected process) │
   │                │   on SQLite)       └──────────┬───────────┘
   └────────────────┘                               │ Kombu
                                                    ▼
                                     ┌─────────────────────────────┐
                                     │  galaxy_queue_worker        │
                                     │  control task fan-out:      │
                                     │   • history_update          │
                                     │   • entry_point_update      │
                                     │   • notification_update     │
                                     │   • broadcast_update        │
                                     └──────────────┬──────────────┘
                                                    │ in-process
                                                    ▼
                              ┌─────────────────────────────────────┐
                              │  Each gunicorn worker:              │
                              │   SSEConnectionManager → asyncio    │
                              │   queue per connected browser tab   │
                              └──────────────┬──────────────────────┘
                                             │ HTTP chunked
                                             ▼
                              ┌─────────────────────────────────────┐
                              │  Browser EventSource                │
                              │  (single stream, multiplexed events)│
                              └─────────────────────────────────────┘
```

Concretely:

1. **One stream per browser, many event types.** The browser opens a single
   `EventSource` against `/api/events/stream`. The same connection carries
   `history_update`, `entry_point_update`, `notification_update`,
   `broadcast_update`, and `notification_status` events.
2. **Per-process registries.** Each Gunicorn worker keeps an
   `SSEConnectionManager` that holds an `asyncio.Queue` per connected tab,
   indexed by user id (and Galaxy session id, so anonymous users still
   receive their own history's updates).
3. **Producers.**
   - History updates come from a `HistoryAuditMonitor` that watches
     `history_audit` via PostgreSQL `LISTEN/NOTIFY` (instant) or by polling
     the audit table on SQLite. Only one process in the cluster is the
     producer, picked by `DatabaseHeartbeat` leader election. If a
     standalone `galaxy-sse-monitor` process is running it always wins;
     otherwise one webapp picks it up.
   - Entry-point updates are dispatched directly from the code paths that
     mutate interactive-tool entry points — there is no separate watcher.
   - Notifications dispatch SSE events from `NotificationManager` whenever
     a notification or broadcast is created.
4. **Cross-process fan-out.** Producers don't know which worker holds the
   recipient's connection, so all events go through a Kombu control task
   broadcast on the internal AMQP bus. Every worker receives every event
   and locally drops the ones for users it doesn't currently hold a
   connection for.
5. **Reconnect catch-up.** When a browser reconnects after a network blip,
   it sends `Last-Event-ID`. The server replays an aggregated
   `notification_status` covering everything since that timestamp. History
   updates come with an `update_time` cursor in the payload, so the client
   can request the delta itself.

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

This controls **all three** SSE-driven paths (history, entry-point,
notifications). When `false`:

- `HistoryAuditMonitor` is not registered, so the cluster does no
  `LISTEN/NOTIFY` or audit-table polling for history changes.
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

When statsd is configured (via `statsd_host` and friends), the SSE
plumbing emits the following metrics. Capture these on the same dashboard
you use for Gunicorn worker health:

| Metric                                     | Type    | Source                | Meaning                                                      |
| ------------------------------------------ | ------- | --------------------- | ------------------------------------------------------------ |
| `galaxy.sse.connections.dropped`           | counter | `SSEConnectionManager` | A per-connection asyncio queue filled up; an event was lost. |
| `galaxy.sse.dispatch.count` (tag: `task`) | counter | `SSEEventDispatcher`  | Control-task fan-outs by event kind.                         |
| `galaxy.sse.dispatch.latency_ms` (tag: `task`) | timing | `SSEEventDispatcher`  | Wall time spent enqueueing the control task.                 |
| `galaxy.sse.dispatch.skipped_no_qw`        | counter | `SSEEventDispatcher`  | Producer tried to dispatch with no queue worker bound — events would have been dropped. |

You can also expose a "currently connected SSE clients" gauge if you wire
one up: each `SSEConnectionManager` instance publishes
`total_broadcast_connections` (all connections, including anonymous) and
`total_per_user_connections` (connections bound to a specific user). These
are per-worker numbers; sum across workers for a cluster total.

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
   for each event kind your users exercise. If you wired up the
   connection gauges, they should reflect roughly one connection per
   open browser tab.

If the connection opens but no events arrive, the most common causes
are: a proxy buffering responses (revisit the NGINX section), or a
producer that can't reach AMQP (see `galaxy.sse.dispatch.skipped_no_qw`).
