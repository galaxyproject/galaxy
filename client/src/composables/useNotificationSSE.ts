import { onScopeDispose, ref } from "vue";

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
}

function sseGlobals(): SSEDebugGlobals {
    return window as unknown as SSEDebugGlobals;
}

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
const subscribers: Map<SSEEventType, Set<Handler>> = new Map();
// Track the per-type dispatchers we registered so ``closeSource`` removes the
// exact same listeners (``addEventListener`` matches by reference).
const dispatchers: Map<SSEEventType, Handler> = new Map();

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
        // Global readiness flag so Selenium tests can distinguish a working
        // SSE pipeline from the polling fallback.
        sseGlobals().__galaxy_sse_connected = true;
    };

    sharedSource.onerror = () => {
        // EventSource auto-reconnects natively; SSE-vs-polling is a
        // config-level decision (see historyStore / notificationsStore), so
        // we must not give up on transient errors here — doing so would leave
        // the client with no updates at all.
        sharedConnected.value = false;
        sseGlobals().__galaxy_sse_connected = false;
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
    }
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
    if (typeof window !== "undefined") {
        window.removeEventListener("pagehide", closeSource);
    }
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
 * The browser's EventSource handles reconnection automatically and sends the
 * ``Last-Event-ID`` header so the server can catch up on missed events. Only
 * one EventSource is opened per tab regardless of how many callers invoke
 * this composable; the composable multiplexes dispatch per event type.
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
