import { onScopeDispose, readonly, ref } from "vue";

import { withPrefix } from "@/utils/redirect";

/**
 * All SSE event types the server may emit.
 */
export const SSE_EVENT_TYPES = [
    "notification_update",
    "broadcast_update",
    "notification_status",
    "history_update",
    "entry_point_update",
] as const;

export type SSEEventType = (typeof SSE_EVENT_TYPES)[number];

interface SSEDebugGlobals {
    __galaxy_sse_connected?: boolean;
    __galaxy_sse_last_event_ts?: number;
    __galaxy_sse_reconnect_attempts?: number;
}

function sseGlobals(): SSEDebugGlobals {
    return window as unknown as SSEDebugGlobals;
}

// Full-jitter exponential backoff bounds for managed reconnect. Aligned with
// the retry budget shape used by the polling paths (see
// ``isRetryableApiError`` in ``client/src/utils/simple-error.ts``); 30 s caps
// the delay during sustained 429/5xx so the client doesn't drift to minutes.
const RECONNECT_BASE_MS = 1000;
const RECONNECT_CAP_MS = 30_000;

// ---------------------------------------------------------------------------
// Module-level shared EventSource.
//
// Every call to ``useSSE`` registers its handler against this one socket so
// the tab opens a single ``/api/events/stream`` connection no matter how many
// stores listen. HTTP/1.1 caps simultaneous connections per origin at six;
// before this consolidation we burned three slots on SSE alone (history,
// notifications, entry points), which is what starved the scratchbook iframe
// flow — see the fix in ``client/src/entry/analysis/App.vue``.
// ---------------------------------------------------------------------------

type Handler = (event: MessageEvent) => void;

let sharedSource: EventSource | null = null;
const sharedConnected = ref(false);
// True once the SSE connection has succeeded at least once in this session.
// Used by UI to distinguish "still connecting" from "was connected, dropped"
// — only the latter should surface a connection-lost warning.
const sseEverConnected = ref(false);
const subscribers: Map<SSEEventType, Set<Handler>> = new Map();
// Track the per-type dispatchers we registered so ``closeSource`` removes the
// exact same listeners (``addEventListener`` matches by reference).
const dispatchers: Map<SSEEventType, Handler> = new Map();

// Managed-reconnect state. We take over from the browser's native auto-retry
// once it flags ``readyState === CLOSED`` so that responses lacking a
// ``text/event-stream`` content type (a 429 / 5xx page, an HTML error page
// from a load balancer, etc.) don't strand the client on the polling
// fallback. ``reconnectAttempts`` is the input to the backoff formula and is
// reset to zero on every successful ``onopen``.
let reconnectAttempts = 0;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

function openSourceIfNeeded() {
    if (sharedSource) {
        return;
    }
    sharedSource = new EventSource(withPrefix("/api/events/stream"));

    for (const eventType of SSE_EVENT_TYPES) {
        const dispatcher: Handler = (event) => {
            // Selenium tests watch ``__galaxy_sse_last_event_ts`` to prove that
            // an observable state change came from an SSE push and not the
            // polling fallback (where the global would never advance).
            sseGlobals().__galaxy_sse_last_event_ts = Date.now();
            const subs = subscribers.get(eventType);
            if (!subs) {
                return;
            }
            for (const handler of subs) {
                handler(event);
            }
        };
        dispatchers.set(eventType, dispatcher);
        sharedSource.addEventListener(eventType, dispatcher);
    }

    sharedSource.onopen = () => {
        sharedConnected.value = true;
        sseEverConnected.value = true;
        // Global readiness flag so Selenium tests can distinguish a working
        // SSE pipeline from the polling fallback.
        sseGlobals().__galaxy_sse_connected = true;
        // The connection is healthy again — drop any pending managed reopen
        // and zero the backoff so the next failure starts at the base delay
        // rather than wherever the previous outage left off.
        reconnectAttempts = 0;
        if (reconnectTimer !== null) {
            clearTimeout(reconnectTimer);
            reconnectTimer = null;
        }
        // Re-assert any viewer subscriptions the user accumulated. The server
        // doesn't carry app-level subscription state across reconnects (it
        // only knows the user from the cookie), so the client owns the source
        // of truth and replays it on every successful open.
        replayViewerSubscriptionsOnOpen();
    };

    sharedSource.onerror = () => {
        sharedConnected.value = false;
        sseGlobals().__galaxy_sse_connected = false;
        // The browser auto-retries while ``readyState === CONNECTING``; let
        // it. Once it flips to ``CLOSED`` (response missing
        // ``text/event-stream``, repeated network failure giving up, etc.)
        // the native loop is done and we own the reconnect — otherwise the
        // client silently drops to polling-only updates for the rest of the
        // session.
        if (sharedSource?.readyState === EventSource.CLOSED) {
            scheduleReconnect();
        }
    };

    // Browser EventSource teardown during a full-page navigation
    // (``window.location.href = …``) is not guaranteed to happen before the
    // browser issues requests for the new page — we've seen Chrome keep the
    // stream alive long enough that a login/register POST reload races the
    // close, and the new page then loads with a stale auth view. Force a
    // synchronous ``close()`` during ``pagehide`` (fires for both reloads and
    // tab-close, unlike ``beforeunload``) to close that window.
    if (typeof window !== "undefined") {
        window.addEventListener("pagehide", closeSource);
        // Background tabs throttle/suspend the timers that both the browser's
        // native EventSource retry and our ``scheduleReconnect`` backoff rely
        // on, so a drop while the tab is hidden can sit un-recovered until the
        // user comes back. Force an immediate reopen when the tab is
        // refocused or connectivity returns. This only cycles the SSE socket —
        // it never starts polling — so it stays consistent with the SSE-mode
        // design decision documented in ``historyStore.ts``. Re-adding the
        // same function reference is idempotent, so calling this on every
        // reopen does not stack listeners.
        window.addEventListener("online", handleWakeReconnect);
    }
    if (typeof document !== "undefined") {
        document.addEventListener("visibilitychange", handleWakeReconnect);
    }
}

// Force an immediate reconnect when the tab wakes up (refocus) or the network
// comes back, but only when we're actually disconnected so we never tear down
// a healthy stream.
function handleWakeReconnect() {
    if (typeof document !== "undefined" && document.visibilityState !== "visible") {
        return;
    }
    if (sharedConnected.value) {
        return;
    }
    reconnectSSE();
}

function closeSource() {
    if (!sharedSource) {
        return;
    }
    for (const [eventType, dispatcher] of dispatchers) {
        sharedSource.removeEventListener(eventType, dispatcher);
    }
    dispatchers.clear();
    sharedSource.close();
    sharedSource = null;
    sharedConnected.value = false;
    sseGlobals().__galaxy_sse_connected = false;
    // Cancel any pending managed reopen — without this, ``pagehide``-driven
    // teardown could be followed by ``setTimeout`` re-opening a stream we
    // just deliberately closed.
    if (reconnectTimer !== null) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
    }
    reconnectAttempts = 0;
    if (typeof window !== "undefined") {
        window.removeEventListener("pagehide", closeSource);
        window.removeEventListener("online", handleWakeReconnect);
    }
    if (typeof document !== "undefined") {
        document.removeEventListener("visibilitychange", handleWakeReconnect);
    }
}

/**
 * Tear down the EventSource without disturbing the subscriber map so the
 * scheduled reopen ends up wired to the same handler set. ``closeSource`` is
 * the right tool when *no* listener wants more events; this is the right tool
 * when listeners still exist and only the underlying socket needs to cycle.
 */
function closeSourceForReconnect() {
    if (!sharedSource) {
        return;
    }
    for (const [eventType, dispatcher] of dispatchers) {
        sharedSource.removeEventListener(eventType, dispatcher);
    }
    dispatchers.clear();
    sharedSource.close();
    sharedSource = null;
    sharedConnected.value = false;
    sseGlobals().__galaxy_sse_connected = false;
}

function scheduleReconnect() {
    if (reconnectTimer !== null) {
        // Already armed; the active timer will handle the next attempt.
        return;
    }
    // Full-jitter exponential backoff: the random factor in [0.5, 1.5)
    // smears retries from clients hitting the same outage so a recovering
    // server isn't met with a synchronized stampede.
    const exp = Math.min(RECONNECT_CAP_MS, RECONNECT_BASE_MS * 2 ** reconnectAttempts);
    const delay = Math.floor(exp * (0.5 + Math.random()));
    reconnectAttempts += 1;
    const globals = sseGlobals();
    globals.__galaxy_sse_reconnect_attempts = (globals.__galaxy_sse_reconnect_attempts ?? 0) + 1;
    closeSourceForReconnect();
    reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        // Subscribers may have all unsubscribed during the outage; if so, the
        // shared source should stay closed.
        let hasSubscribers = false;
        for (const subs of subscribers.values()) {
            if (subs.size > 0) {
                hasSubscribers = true;
                break;
            }
        }
        if (hasSubscribers) {
            openSourceIfNeeded();
        }
    }, delay);
}

/**
 * Force an immediate reconnect, bypassing the backoff schedule. Used by the
 * "Live updates disconnected. Click to refresh." button and by the
 * wake/online listeners — situations where the user (or a regained-focus
 * signal) wants the stream back *now* rather than on the next backed-off
 * ``setTimeout`` tick, which a backgrounded tab may have suspended.
 */
export function reconnectSSE(): void {
    // Nothing wants events; leave the source closed.
    let hasSubscribers = false;
    for (const subs of subscribers.values()) {
        if (subs.size > 0) {
            hasSubscribers = true;
            break;
        }
    }
    if (!hasSubscribers) {
        return;
    }
    // Drop any pending managed reopen and zero the backoff so this reopen
    // happens immediately and the next failure starts at the base delay.
    if (reconnectTimer !== null) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
    }
    reconnectAttempts = 0;
    // Cycle the socket while keeping the subscriber map intact — covers both a
    // source stuck in CONNECTING and one already CLOSED.
    closeSourceForReconnect();
    openSourceIfNeeded();
}

function addSubscriber(onEvent: Handler, eventTypes: readonly SSEEventType[]) {
    for (const eventType of eventTypes) {
        let subs = subscribers.get(eventType);
        if (!subs) {
            subs = new Set();
            subscribers.set(eventType, subs);
        }
        subs.add(onEvent);
    }
}

function removeSubscriber(onEvent: Handler, eventTypes: readonly SSEEventType[]): boolean {
    let anyRemaining = false;
    for (const eventType of eventTypes) {
        const subs = subscribers.get(eventType);
        if (subs) {
            subs.delete(onEvent);
            if (subs.size === 0) {
                subscribers.delete(eventType);
            }
        }
    }
    for (const subs of subscribers.values()) {
        if (subs.size > 0) {
            anyRemaining = true;
            break;
        }
    }
    return anyRemaining;
}

/**
 * Composable for subscribing to events on the shared SSE stream.
 *
 * Reconnection: the browser's native auto-retry handles the cheap path
 * (transient network blips while ``readyState === CONNECTING``); once the
 * source flips to ``CLOSED`` — typically a 4xx/5xx response with no
 * ``text/event-stream`` body, which most browsers treat as fatal — this
 * composable takes over with full-jitter exponential backoff capped at 30 s.
 * The server emits ``id:`` per event so the ``Last-Event-ID`` header on
 * reconnect lets the server catch up on missed events. Only one EventSource
 * is opened per tab regardless of how many callers invoke this composable;
 * the composable multiplexes dispatch per event type.
 *
 * @param onEvent - callback invoked for every matching SSE event
 * @param eventTypes - subset of event types to listen to (defaults to all)
 */
export function useSSE(onEvent: Handler, eventTypes: readonly SSEEventType[] = SSE_EVENT_TYPES) {
    let connected_: boolean = false;

    function connect() {
        if (connected_) {
            return;
        }
        connected_ = true;
        addSubscriber(onEvent, eventTypes);
        openSourceIfNeeded();
    }

    function disconnect() {
        if (!connected_) {
            return;
        }
        connected_ = false;
        const anyRemaining = removeSubscriber(onEvent, eventTypes);
        if (!anyRemaining) {
            closeSource();
        }
    }

    onScopeDispose(() => {
        disconnect();
    });

    return { connect, disconnect, connected: sharedConnected };
}

/**
 * @deprecated Use `useSSE` instead. This alias exists for backward compatibility.
 */
export const useNotificationSSE = useSSE;

/**
 * Read-only handle on the shared SSE connection state. ``connected`` flips
 * with the EventSource lifecycle; ``hasEverConnected`` latches true on the
 * first successful open so callers can ignore the initial-connect window
 * when surfacing a "connection lost" warning. ``reconnect`` forces an
 * immediate reopen for "click to refresh" affordances.
 */
export function useSSEConnectionStatus() {
    return {
        connected: readonly(sharedConnected),
        hasEverConnected: readonly(sseEverConnected),
        reconnect: reconnectSSE,
    };
}

// ---------------------------------------------------------------------------
// Viewer subscriptions for non-owned histories
//
// Owner routing already covers history_update events for histories the
// current user owns. Watching a non-owned history (e.g. a shared history
// pinned in the multi-history view) requires the client to opt in by POSTing
// the history id to ``/api/events/history-subscriptions``. The server keeps a
// per-worker map and pushes the same history_update events to every viewer
// in that map. The desired set is held module-level so reconnects can
// replay it and so multiple components subscribed to the same id only emit
// one HTTP call.
// ---------------------------------------------------------------------------

const viewerSubscriptions = new Map<string, number>();

function postViewerSubscription(method: "POST" | "DELETE", historyIds: string[]): Promise<void> {
    if (historyIds.length === 0) {
        return Promise.resolve();
    }
    return fetch(withPrefix("/api/events/history-subscriptions"), {
        method,
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ history_ids: historyIds }),
    }).then((response) => {
        if (!response.ok) {
            throw new Error(`history-subscriptions ${method} failed: ${response.status}`);
        }
    });
}

function replayViewerSubscriptionsOnOpen(): void {
    const ids = [...viewerSubscriptions.keys()];
    if (ids.length === 0) {
        return;
    }
    postViewerSubscription("POST", ids).catch((err) =>
        console.error("Failed to replay history viewer subscriptions on reconnect:", err),
    );
}

/**
 * Add a viewer subscription for a history this user does not own. Refcounted
 * so two components watching the same history share one server-side
 * subscription and the first to mount opens it, last to unmount closes it.
 *
 * Idempotent per call: re-subscribing an already-tracked id does not POST a
 * duplicate.
 */
export function addHistoryViewerSubscription(historyId: string): void {
    const previous = viewerSubscriptions.get(historyId) ?? 0;
    viewerSubscriptions.set(historyId, previous + 1);
    if (previous === 0) {
        postViewerSubscription("POST", [historyId]).catch((err) =>
            console.error(`Failed to subscribe to history ${historyId}:`, err),
        );
    }
}

export function removeHistoryViewerSubscription(historyId: string): void {
    const previous = viewerSubscriptions.get(historyId);
    if (!previous) {
        return;
    }
    if (previous > 1) {
        viewerSubscriptions.set(historyId, previous - 1);
        return;
    }
    viewerSubscriptions.delete(historyId);
    postViewerSubscription("DELETE", [historyId]).catch((err) =>
        console.error(`Failed to unsubscribe from history ${historyId}:`, err),
    );
}

/** Test-only: drain the desired set so per-test state doesn't leak. */
export function _resetHistoryViewerSubscriptionsForTest(): void {
    viewerSubscriptions.clear();
}

/** Test-only: tear down the shared source and reconnect state. */
export function _resetSSESharedSourceForTest(): void {
    if (reconnectTimer !== null) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
    }
    reconnectAttempts = 0;
    if (sharedSource) {
        for (const [eventType, dispatcher] of dispatchers) {
            sharedSource.removeEventListener(eventType, dispatcher);
        }
        dispatchers.clear();
        sharedSource.close();
        sharedSource = null;
    }
    subscribers.clear();
    sharedConnected.value = false;
    sseEverConnected.value = false;
    const globals = sseGlobals();
    delete globals.__galaxy_sse_connected;
    delete globals.__galaxy_sse_last_event_ts;
    delete globals.__galaxy_sse_reconnect_attempts;
}
