import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { useServerMock } from "@/api/client/__mocks__";

import { useHistoryStore } from "./historyStore";

// Capture SSE composable usage — neither test should rely on the real
// EventSource. The `connected` ref stays false by default; the store must
// NOT key polling behavior off it.
const mockSseConnect = vi.fn();
const mockSseDisconnect = vi.fn();
const mockSseConnected = ref(false);

vi.mock("@/composables/useNotificationSSE", () => ({
    useSSE: vi.fn(() => ({
        connect: mockSseConnect,
        disconnect: mockSseDisconnect,
        connected: mockSseConnected,
    })),
}));

// `watchHistory(app)` is the polling handler invoked on the short/long
// interval. We mock it so each invocation is observable without pulling in
// the history-items store, dataset store, and Galaxy app instance.
const mockWatchHistory = vi.fn().mockResolvedValue(undefined);
const mockRefreshHistoryFromPush = vi.fn().mockResolvedValue(undefined);
vi.mock("@/watch/watchHistory", () => ({
    ACTIVE_POLLING_INTERVAL: 3000,
    INACTIVE_POLLING_INTERVAL: 60_000,
    watchHistory: (app: unknown) => mockWatchHistory(app),
    refreshHistoryFromPush: (app: unknown) => mockRefreshHistoryFromPush(app),
}));

vi.mock("@/app", () => ({
    getGalaxyInstance: () => ({ name: "fake-galaxy" }),
}));

const { server, http } = useServerMock();

function configResponse(enableSse: boolean) {
    return { enable_sse_history_updates: enableSse };
}

function registerDefaultHandlers({ enableSse }: { enableSse: boolean }) {
    server.use(
        http.get("/api/configuration", ({ response }) => {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            return response(200).json(configResponse(enableSse) as any);
        }),
    );
}

describe("historyStore — config-driven SSE vs polling", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        mockSseConnect.mockClear();
        mockSseDisconnect.mockClear();
        mockSseConnected.value = false;
        mockWatchHistory.mockClear();
        mockRefreshHistoryFromPush.mockClear();
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    describe("when enable_sse_history_updates is true (SSE scenario)", () => {
        beforeEach(() => {
            registerDefaultHandlers({ enableSse: true });
        });

        it("primes the store with one initial load, connects SSE, and does not keep polling", async () => {
            const store = useHistoryStore();

            // `startWatchingHistory` is an exported alias for
            // `startWatchingHistoryWithSSE` (see historyStore.ts).
            store.startWatchingHistory();

            // Config loads async; let the watch fire.
            await flushPromises();
            await vi.runOnlyPendingTimersAsync();
            await flushPromises();

            expect(mockSseConnect).toHaveBeenCalledTimes(1);
            // One-shot initial fetch so the history panel isn't empty before
            // the first SSE event arrives.
            expect(mockWatchHistory).toHaveBeenCalledTimes(1);

            // Advance past the short polling interval (3s) several times and
            // confirm the polling handler is not invoked a second time in SSE mode.
            vi.advanceTimersByTime(30_000);
            await flushPromises();
            expect(mockWatchHistory).toHaveBeenCalledTimes(1);
        });

        it("does not start polling when the tab regains visibility", async () => {
            const store = useHistoryStore();
            store.startWatchingHistory();
            await flushPromises();
            await vi.runOnlyPendingTimersAsync();
            await flushPromises();
            expect(mockWatchHistory).toHaveBeenCalledTimes(1);

            // Simulate a tab hide/show cycle. `useResourceWatcher` registers
            // a `visibilitychange` listener whose handler calls
            // `startWatchingResourceIfNeeded` — in SSE mode that would
            // silently resume polling. Because we never instantiated the
            // watcher, no listener should exist and no poll should fire.
            Object.defineProperty(document, "visibilityState", {
                configurable: true,
                get: () => "hidden",
            });
            document.dispatchEvent(new Event("visibilitychange"));
            Object.defineProperty(document, "visibilityState", {
                configurable: true,
                get: () => "visible",
            });
            document.dispatchEvent(new Event("visibilitychange"));

            await flushPromises();
            vi.advanceTimersByTime(30_000);
            await flushPromises();
            expect(mockWatchHistory).toHaveBeenCalledTimes(1);
        });
    });

    describe("when enable_sse_history_updates is false (polling scenario)", () => {
        beforeEach(() => {
            registerDefaultHandlers({ enableSse: false });
        });

        it("does not connect SSE and polls on the configured interval", async () => {
            const store = useHistoryStore();

            store.startWatchingHistory();

            // Let the config load and the initial watch fire.
            await flushPromises();
            await vi.runOnlyPendingTimersAsync();
            await flushPromises();

            expect(mockSseConnect).not.toHaveBeenCalled();

            // The resource watcher invokes the handler immediately on start
            // and then re-schedules after each completion. Advance past the
            // short interval and confirm repeated invocations.
            const initialCalls = mockWatchHistory.mock.calls.length;
            expect(initialCalls).toBeGreaterThanOrEqual(1);

            await vi.advanceTimersByTimeAsync(3000);
            await flushPromises();
            expect(mockWatchHistory.mock.calls.length).toBeGreaterThan(initialCalls);
        });

        it("calling startWatchingHistory again is idempotent (no second SSE, polling already running)", async () => {
            const store = useHistoryStore();

            store.startWatchingHistory();
            await flushPromises();
            await vi.runOnlyPendingTimersAsync();
            await flushPromises();

            const pollsAfterFirst = mockWatchHistory.mock.calls.length;

            store.startWatchingHistory();
            await flushPromises();

            expect(mockSseConnect).not.toHaveBeenCalled();
            // Calling again does not schedule an additional independent
            // polling loop — the handler should not have been fired an
            // extra time by the second call alone.
            expect(mockWatchHistory.mock.calls.length).toBe(pollsAfterFirst);
        });
    });
});
