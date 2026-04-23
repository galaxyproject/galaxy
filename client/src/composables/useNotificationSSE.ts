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

/**
 * Composable for connecting to the unified SSE event stream.
 *
 * The browser's EventSource handles reconnection automatically and
 * sends the Last-Event-ID header so the server can catch up on missed events.
 *
 * @param onEvent - callback invoked for every SSE event
 * @param eventTypes - subset of event types to listen to (defaults to all)
 */
export function useSSE(onEvent: (event: MessageEvent) => void, eventTypes: readonly SSEEventType[] = SSE_EVENT_TYPES) {
    const connected = ref(false);
    let eventSource: EventSource | null = null;

    // Selenium tests watch __galaxy_sse_last_event_ts to prove that an
    // observable state change came from an SSE push and not the polling
    // fallback (where __galaxy_sse_last_event_ts would never advance).
    const trackedOnEvent = (event: MessageEvent) => {
        sseGlobals().__galaxy_sse_last_event_ts = Date.now();
        onEvent(event);
    };

    // Browser EventSource teardown during a full-page navigation
    // (``window.location.href = …``) is not guaranteed to happen before the
    // browser issues requests for the new page — we've seen Chrome keep the
    // stream alive long enough that a login/register POST reload races the
    // close, and the new page then loads with a stale auth view. Force a
    // synchronous ``eventSource.close()`` during ``pagehide`` (fires for both
    // reloads and tab-close, unlike ``beforeunload``) to close that window.
    // The listener is registered only while a connection is live so composables
    // that never ``connect()`` don't leave dangling listeners behind.
    const onPageHide = () => disconnect();

    function connect() {
        disconnect();
        const url = withPrefix("/api/events/stream");
        eventSource = new EventSource(url);

        for (const eventType of eventTypes) {
            eventSource.addEventListener(eventType, trackedOnEvent);
        }

        eventSource.onopen = () => {
            connected.value = true;
            // Expose a global readiness flag so Selenium tests can distinguish
            // a working SSE pipeline from the polling fallback.
            sseGlobals().__galaxy_sse_connected = true;
        };

        eventSource.onerror = () => {
            // EventSource auto-reconnects natively; SSE-vs-polling is a
            // config-level decision (see historyStore / notificationsStore),
            // so we must not give up on transient errors here — doing so
            // would leave the client with no updates at all.
            connected.value = false;
            sseGlobals().__galaxy_sse_connected = false;
        };

        if (typeof window !== "undefined") {
            window.addEventListener("pagehide", onPageHide);
        }
    }

    function disconnect() {
        if (eventSource) {
            for (const eventType of eventTypes) {
                eventSource.removeEventListener(eventType, trackedOnEvent);
            }
            eventSource.close();
            eventSource = null;
        }
        if (typeof window !== "undefined") {
            window.removeEventListener("pagehide", onPageHide);
        }
        connected.value = false;
        sseGlobals().__galaxy_sse_connected = false;
    }

    onScopeDispose(() => {
        disconnect();
    });

    return { connect, disconnect, connected };
}

/**
 * @deprecated Use `useSSE` instead. This alias exists for backward compatibility.
 */
export const useNotificationSSE = useSSE;
