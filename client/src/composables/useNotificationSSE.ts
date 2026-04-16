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
] as const;

export type SSEEventType = (typeof SSE_EVENT_TYPES)[number];

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
    let consecutiveErrors = 0;

    function connect() {
        disconnect();
        consecutiveErrors = 0;
        const url = withPrefix("/api/events/stream");
        eventSource = new EventSource(url);

        for (const eventType of eventTypes) {
            eventSource.addEventListener(eventType, onEvent);
        }

        eventSource.onopen = () => {
            connected.value = true;
            consecutiveErrors = 0;
            // Expose a global readiness flag so Selenium tests can distinguish
            // a working SSE pipeline from the polling fallback.
            (window as unknown as { __galaxy_sse_connected?: boolean }).__galaxy_sse_connected = true;
        };

        eventSource.onerror = () => {
            connected.value = false;
            (window as unknown as { __galaxy_sse_connected?: boolean }).__galaxy_sse_connected = false;
            consecutiveErrors++;
            // EventSource auto-reconnects, but if we get too many errors
            // in a row, the server likely doesn't support SSE — give up
            // and let the caller fall back to polling.
            if (consecutiveErrors > 5) {
                disconnect();
            }
        };
    }

    function disconnect() {
        if (eventSource) {
            for (const eventType of eventTypes) {
                eventSource.removeEventListener(eventType, onEvent);
            }
            eventSource.close();
            eventSource = null;
        }
        connected.value = false;
        (window as unknown as { __galaxy_sse_connected?: boolean }).__galaxy_sse_connected = false;
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
