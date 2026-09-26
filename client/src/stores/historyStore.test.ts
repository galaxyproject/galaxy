import flushPromises from "flush-promises";
import { http as mswHttp } from "msw";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import { emitSse, sseMockFactory, useVisibilityPatch } from "./_testing/sseStoreSupport";
import { useHistoryStore } from "./historyStore";
import * as userQueries from "./users/queries";
import { useUserStore } from "./userStore";

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
            return response(200).json({ enable_sse_updates: enableSse } as any);
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

    describe("when enable_sse_updates is true (SSE scenario)", () => {
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
            // This test asserts the store's *decision* to refresh, not the refresh
            // itself — ``refreshHistoryFromPush`` is mocked so we can observe the
            // dispatch. The real refresh is covered end-to-end in the Selenium
            // SSE integration tests (see test/integration_selenium/test_history_sse.py).
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

    describe("when enable_sse_updates is false (polling scenario)", () => {
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
            // Exactly one additional poll after the 3000ms advance — anything
            // else means a second independent polling loop was scheduled.
            const deltaAfterSecond = mockWatchHistory.mock.calls.length - pollsAfterFirst;
            expect(deltaAfterSecond).toBe(1);
        });
    });
});

describe("history loading failures during user initialization", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        vi.spyOn(userQueries, "getCurrentUser").mockResolvedValue(null);
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it.each([1, 2])("allows retry after history count request %i fails", async (failedRequest) => {
        let countRequests = 0;
        const listRequest = vi.fn();
        server.use(
            mswHttp.get("/api/histories/count", () => {
                countRequests++;
                return countRequests === failedRequest ? HttpResponse.error() : HttpResponse.json(1);
            }),
            http.get("/api/histories", () => {
                listRequest();
                return HttpResponse.json([{ id: "history-1", name: "Test history", genome_build: "?" }]);
            }),
        );
        const userStore = useUserStore();
        const historyStore = useHistoryStore();

        // Concurrent callers share the failing initialization request.
        const results = await Promise.allSettled([userStore.loadUser(), userStore.loadUser()]);
        expect(results.map((result) => result.status)).toEqual(["rejected", "rejected"]);
        expect(userQueries.getCurrentUser).toHaveBeenCalledTimes(1);
        expect(countRequests).toBe(failedRequest);
        expect(historyStore.historiesLoading).toBe(false);

        await expect(userStore.loadUser()).resolves.toBeUndefined();
        expect(userQueries.getCurrentUser).toHaveBeenCalledTimes(2);
        expect(historyStore.historiesLoading).toBe(false);
        expect(listRequest).toHaveBeenCalledTimes(1);
        expect(historyStore.totalHistoryCount).toBe(1);

        // Successful initialization remains cached.
        await userStore.loadUser();
        expect(userQueries.getCurrentUser).toHaveBeenCalledTimes(2);
    });

    it("allows user-only initialization after history loading fails", async () => {
        server.use(mswHttp.get("/api/histories/count", () => HttpResponse.error()));
        const userStore = useUserStore();
        await expect(userStore.loadUser()).rejects.toThrow();
        await expect(userStore.loadUser(false)).resolves.toBeUndefined();
        expect(userQueries.getCurrentUser).toHaveBeenCalledTimes(2);
    });
});
