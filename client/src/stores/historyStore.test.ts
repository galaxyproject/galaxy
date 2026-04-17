import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import { emitSse, sseMockFactory, useVisibilityPatch } from "./_testing/sseStoreSupport";
import { useHistoryStore } from "./historyStore";

// ``vi.mock`` is hoisted above module-level ``const`` declarations, so the
// capture-state has to be built via ``vi.hoisted`` to be visible to the factory.
const sseState = vi.hoisted(() => {
    return {
        onEvent: null as ((event: MessageEvent) => void) | null,
        connect: vi.fn(),
        disconnect: vi.fn(),
    };
});

vi.mock("@/composables/useNotificationSSE", () => sseMockFactory(sseState));

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

function registerDefaultHandlers({ enableSse }: { enableSse: boolean }) {
    server.use(
        http.get("/api/configuration", ({ response }) => {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            return response(200).json({ enable_sse_history_updates: enableSse } as any);
        }),
    );
}

async function primeStore(startFn: () => void): Promise<void> {
    startFn();
    // Config load is async; let the watch fire and the initial fetch complete.
    await flushPromises();
    await vi.runOnlyPendingTimersAsync();
    await flushPromises();
}

describe("historyStore — config-driven SSE vs polling", () => {
    let visibility: ReturnType<typeof useVisibilityPatch>;

    beforeEach(() => {
        setActivePinia(createPinia());
        sseState.connect.mockClear();
        sseState.disconnect.mockClear();
        sseState.onEvent = null;
        mockWatchHistory.mockClear();
        mockRefreshHistoryFromPush.mockClear();
        vi.useFakeTimers();
        visibility = useVisibilityPatch();
    });

    afterEach(() => {
        visibility.restore();
        vi.useRealTimers();
    });

    describe("when enable_sse_history_updates is true (SSE scenario)", () => {
        beforeEach(() => {
            registerDefaultHandlers({ enableSse: true });
        });

        it("primes the store with one initial load, connects SSE, and does not keep polling", async () => {
            const store = useHistoryStore();
            await primeStore(() => store.startWatchingHistory());

            expect(sseState.connect).toHaveBeenCalledTimes(1);
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
            await primeStore(() => store.startWatchingHistory());
            expect(mockWatchHistory).toHaveBeenCalledTimes(1);

            // Simulate a tab hide/show cycle. `useResourceWatcher` registers
            // a `visibilitychange` listener whose handler calls
            // `startWatchingResourceIfNeeded` — in SSE mode that would
            // silently resume polling. Because we never instantiated the
            // watcher, no listener should exist and no poll should fire.
            visibility.set("hidden");
            visibility.set("visible");

            await flushPromises();
            vi.advanceTimersByTime(30_000);
            await flushPromises();
            expect(mockWatchHistory).toHaveBeenCalledTimes(1);
        });

        it("triggers refreshHistoryFromPush when an SSE event names the current history", async () => {
            const store = useHistoryStore();
            await primeStore(() => store.startWatchingHistory());
            // Drive the store to a known current-history id so the handler has
            // something to match against. ``currentHistoryId`` is a computed
            // that only returns the stored id when the history is present in
            // ``storedHistories``, so the history has to be registered too.
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            store.setHistory({ id: "hist-1" } as any);
            store.setCurrentHistoryId("hist-1");

            mockRefreshHistoryFromPush.mockClear();
            emitSse(sseState, "history_update", { history_ids: ["hist-1", "hist-2"] });
            await flushPromises();

            expect(mockRefreshHistoryFromPush).toHaveBeenCalledTimes(1);
        });

        it("ignores SSE history events that do not include the current history", async () => {
            const store = useHistoryStore();
            await primeStore(() => store.startWatchingHistory());
            store.setCurrentHistoryId("hist-1");

            mockRefreshHistoryFromPush.mockClear();
            emitSse(sseState, "history_update", { history_ids: ["hist-2"] });
            await flushPromises();

            expect(mockRefreshHistoryFromPush).not.toHaveBeenCalled();
        });
    });

    describe("when enable_sse_history_updates is false (polling scenario)", () => {
        beforeEach(() => {
            registerDefaultHandlers({ enableSse: false });
        });

        it("does not connect SSE and polls on the configured interval", async () => {
            const store = useHistoryStore();
            await primeStore(() => store.startWatchingHistory());

            expect(sseState.connect).not.toHaveBeenCalled();

            // The resource watcher invokes the handler immediately on start
            // and then re-schedules after each completion. Advance past the
            // short interval and confirm repeated invocations.
            const initialCalls = mockWatchHistory.mock.calls.length;
            expect(initialCalls).toBeGreaterThanOrEqual(1);

            await vi.advanceTimersByTimeAsync(3000);
            await flushPromises();
            expect(mockWatchHistory.mock.calls.length).toBeGreaterThan(initialCalls);
        });

        it("calling startWatchingHistory again is idempotent (no second SSE, polling tick count +1 only)", async () => {
            const store = useHistoryStore();
            await primeStore(() => store.startWatchingHistory());

            const pollsAfterFirst = mockWatchHistory.mock.calls.length;

            store.startWatchingHistory();
            await flushPromises();

            expect(sseState.connect).not.toHaveBeenCalled();
            // Calling again must not schedule a second independent polling loop.
            // Advance past one interval and confirm only one handler tick fires,
            // not two.
            await vi.advanceTimersByTimeAsync(3000);
            await flushPromises();
            const deltaAfterSecond = mockWatchHistory.mock.calls.length - pollsAfterFirst;
            expect(deltaAfterSecond).toBeLessThanOrEqual(1);
        });
    });
});
