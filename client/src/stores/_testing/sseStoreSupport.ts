/**
 * Shared test helpers for the SSE-driven stores (historyStore, notificationsStore).
 *
 * Both stores consume the same `useSSE` composable and need:
 *  - a mock that captures the onEvent callback so tests can synthesize SSE messages;
 *  - visibility-state patching without leaking across tests (JSDOM's `document`
 *    is shared by every test in the same worker, so an unrestored
 *    `Object.defineProperty` causes silent bleed).
 *
 * Because ``vi.mock`` is hoisted above module-level variables, tests must
 * construct the SSE-mock state via ``vi.hoisted`` and then hand it to
 * ``sseMockFactory`` from inside the ``vi.mock`` factory. See the ``.test.ts``
 * files in this directory for the pattern.
 */

import { vi } from "vitest";
import { type Ref, ref } from "vue";

export interface SSEMockState {
    onEvent: ((event: MessageEvent) => void) | null;
    connect: ReturnType<typeof vi.fn>;
    disconnect: ReturnType<typeof vi.fn>;
}

/** Build the factory used with ``vi.mock("@/composables/useNotificationSSE", ...)``. */
export function sseMockFactory(state: SSEMockState) {
    return {
        useSSE: vi.fn((onEvent: (event: MessageEvent) => void) => {
            state.onEvent = onEvent;
            return { connect: state.connect, disconnect: state.disconnect };
        }),
    };
}

/** Synthesize an SSE message through the captured handler. */
export function emitSse(state: SSEMockState, type: string, payload: unknown): void {
    if (!state.onEvent) {
        throw new Error("useSSE was not called by the store under test — cannot emit an SSE event");
    }
    state.onEvent(new MessageEvent(type, { data: JSON.stringify(payload) }));
}

/**
 * Save the current ``document.visibilityState`` descriptor and return a restorer.
 * Call the restorer in ``afterEach`` to prevent patching from leaking into later tests.
 */
export function useVisibilityPatch(): {
    set: (state: "visible" | "hidden") => void;
    restore: () => void;
} {
    const original = Object.getOwnPropertyDescriptor(document, "visibilityState");
    return {
        set(state: "visible" | "hidden") {
            Object.defineProperty(document, "visibilityState", {
                configurable: true,
                get: () => state,
            });
            document.dispatchEvent(new Event("visibilitychange"));
        },
        restore() {
            if (original) {
                Object.defineProperty(document, "visibilityState", original);
            } else {
                delete (document as unknown as Record<string, unknown>).visibilityState;
            }
        },
    };
}
