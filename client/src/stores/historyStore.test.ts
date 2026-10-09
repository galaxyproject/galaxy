import { getFakeHistorySummary } from "@tests/test-data";
import type { MockInstance } from "@vitest/spy";
import flushPromises from "flush-promises";
import { http as rawHttp } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { MAX_RETRIES } from "@/utils/simple-error";

import { emitSse, sseMockFactory, useVisibilityPatch } from "./_testing/sseStoreSupport";
import { useHistoryStore } from "./historyStore";
import { setupTestPinia } from "./testUtils";
import * as userQueries from "./users/queries";
import { useUserStore } from "./userStore";

const sseState = vi.hoisted(() => {
    return {
        onEvent: null as ((event: MessageEvent) => void) | null,
        connect: vi.fn(),
        disconnect: vi.fn(),
    };
});

vi.mock("@/composables/useNotificationSSE", () => sseMockFactory(sseState));

// Observe refresh decisions without loading the history-items or dataset stores.
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

function registerSseConfiguration(enableSse: boolean) {
    server.use(
        http.get("/api/configuration", ({ response }) => {
            return response.untyped(HttpResponse.json({ enable_sse_updates: enableSse }));
        }),
    );
}

async function startWatchingHistory(store: ReturnType<typeof useHistoryStore>) {
    store.startWatchingHistory();
    // Let configuration loading trigger the watcher and complete the initial fetch.
    await flushPromises();
    await vi.runOnlyPendingTimersAsync();
    await flushPromises();
}

describe("history updates", () => {
    let visibility: ReturnType<typeof useVisibilityPatch>;
    let addDocumentListener: MockInstance<Document["addEventListener"]>;

    beforeEach(() => {
        setupTestPinia();
        sseState.connect.mockClear();
        sseState.disconnect.mockClear();
        sseState.onEvent = null;
        mockWatchHistory.mockClear();
        mockRefreshHistoryFromPush.mockClear();
        vi.useFakeTimers();
        visibility = useVisibilityPatch();
        addDocumentListener = vi.spyOn(document, "addEventListener");
    });

    afterEach(() => {
        useHistoryStore().stopWatchingHistory();
        useHistoryStore().$dispose();
        // Stopping history polling does not dispose its resource watcher's visibility listener.
        for (const [event, listener, options] of addDocumentListener.mock.calls) {
            if (event === "visibilitychange") {
                document.removeEventListener(event, listener, options);
            }
        }
        addDocumentListener.mockRestore();
        visibility.restore();
        vi.useRealTimers();
    });

    describe("with SSE enabled", () => {
        beforeEach(() => {
            registerSseConfiguration(true);
        });

        it("primes the store with one initial load, connects SSE, and does not keep polling", async () => {
            const store = useHistoryStore();
            await startWatchingHistory(store);

            expect(sseState.connect).toHaveBeenCalledTimes(1);
            expect(mockWatchHistory).toHaveBeenCalledTimes(1);

            vi.advanceTimersByTime(30_000);
            await flushPromises();
            expect(mockWatchHistory).toHaveBeenCalledTimes(1);
        });

        it("does not start polling when the tab regains visibility", async () => {
            const store = useHistoryStore();
            await startWatchingHistory(store);
            expect(mockWatchHistory).toHaveBeenCalledTimes(1);

            visibility.set("hidden");
            visibility.set("visible");

            await flushPromises();
            vi.advanceTimersByTime(30_000);
            await flushPromises();
            expect(mockWatchHistory).toHaveBeenCalledTimes(1);
        });

        it("triggers refreshHistoryFromPush when an SSE event names the current history", async () => {
            const store = useHistoryStore();
            await startWatchingHistory(store);
            store.setHistory(getFakeHistorySummary({ id: "hist-1" }));
            store.setCurrentHistoryId("hist-1");

            mockRefreshHistoryFromPush.mockClear();
            emitSse(sseState, "history_update", { history_ids: ["hist-1", "hist-2"] });
            await flushPromises();

            expect(mockRefreshHistoryFromPush).toHaveBeenCalledTimes(1);
        });

        it("ignores SSE history events that do not include the current history", async () => {
            const store = useHistoryStore();
            await startWatchingHistory(store);
            store.setHistory(getFakeHistorySummary({ id: "hist-1" }));
            store.setCurrentHistoryId("hist-1");
            expect(store.currentHistoryId).toBe("hist-1");

            mockRefreshHistoryFromPush.mockClear();
            emitSse(sseState, "history_update", { history_ids: ["hist-2"] });
            await flushPromises();

            expect(mockRefreshHistoryFromPush).not.toHaveBeenCalled();
        });
    });

    describe("with SSE disabled", () => {
        beforeEach(() => {
            registerSseConfiguration(false);
        });

        it("does not connect SSE and polls on the configured interval", async () => {
            const store = useHistoryStore();
            await startWatchingHistory(store);

            expect(sseState.connect).not.toHaveBeenCalled();

            const initialCalls = mockWatchHistory.mock.calls.length;
            expect(initialCalls).toBeGreaterThanOrEqual(1);

            await vi.advanceTimersByTimeAsync(3000);
            await flushPromises();
            expect(mockWatchHistory.mock.calls.length).toBeGreaterThan(initialCalls);
        });

        it("keeps one polling loop when started twice", async () => {
            const store = useHistoryStore();
            await startWatchingHistory(store);

            const pollsAfterFirst = mockWatchHistory.mock.calls.length;

            store.startWatchingHistory();
            await flushPromises();

            expect(sseState.connect).not.toHaveBeenCalled();
            await vi.advanceTimersByTimeAsync(3000);
            await flushPromises();
            const deltaAfterSecond = mockWatchHistory.mock.calls.length - pollsAfterFirst;
            expect(deltaAfterSecond).toBe(1);
        });
    });
});

describe("creating the current history", () => {
    let requested: string[];

    beforeEach(() => {
        setupTestPinia();
        requested = [];
        server.use(
            http.get("/api/histories/count", ({ response }) => response(200).json(4)),
            // This endpoint creates and selects atomically; a separate POST must go unhandled.
            rawHttp.get("/history/create_new_current", ({ request }) => {
                const name = new URL(request.url).searchParams.get("name");
                requested.push(`create ${name ?? "default"}`);
                return name
                    ? HttpResponse.json({ id: "named-history", name })
                    : HttpResponse.json({ id: "default-history", name: "Unnamed history" });
            }),
            rawHttp.get("/history/set_as_current", ({ request }) => {
                const id = new URL(request.url).searchParams.get("id");
                requested.push(`select ${id}`);
                return HttpResponse.json({ id, name: "RNA run" });
            }),
        );
    });

    it("creates a history with the server's default name", async () => {
        const store = useHistoryStore();

        await store.createNewHistory();

        expect(requested).toEqual(["create default"]);
        expect(store.currentHistoryId).toBe("default-history");
        expect(store.totalHistoryCount).toBe(4);
    });

    it("creates a named history and switches to it", async () => {
        const store = useHistoryStore();

        await store.createNewHistory("RNA run");

        expect(requested).toEqual(["create RNA run"]);
        expect(store.currentHistoryId).toBe("named-history");
        expect(store.totalHistoryCount).toBe(4);
    });

    it.each([
        { name: undefined, description: "an unnamed history" },
        { name: "RNA run", description: "a named history" },
    ])("queues creation of $description behind an in-flight switch", async ({ name }) => {
        let releaseSwitch = () => {};
        const switchPending = new Promise<void>((resolve) => {
            releaseSwitch = resolve;
        });
        server.use(
            rawHttp.get("/history/set_as_current", async ({ request }) => {
                const id = new URL(request.url).searchParams.get("id");
                requested.push(`select ${id}`);
                await switchPending;
                return HttpResponse.json({ id, name: "other" });
            }),
        );
        const store = useHistoryStore();
        const switching = store.setCurrentHistory("other-history");
        await flushPromises();
        const creating = store.createNewHistory(name);
        await flushPromises();
        const beforeRelease = [...requested];
        releaseSwitch();
        await Promise.all([switching, creating]);

        expect(beforeRelease).toEqual(["select other-history"]);
        expect(requested).toEqual(["select other-history", `create ${name ?? "default"}`]);
        expect(store.currentHistoryId).toBe(name ? "named-history" : "default-history");
        expect(store.changingCurrentHistory).toBe(false);
    });

    it.each([
        { name: undefined, description: "an unnamed history" },
        { name: "RNA run", description: "a named history" },
    ])("queues a switch behind creation of $description", async ({ name }) => {
        let releaseCreate = () => {};
        const createPending = new Promise<void>((resolve) => {
            releaseCreate = resolve;
        });
        server.use(
            rawHttp.get("/history/create_new_current", async () => {
                requested.push("create");
                await createPending;
                return HttpResponse.json({ id: "new-history", name: name ?? "Unnamed history" });
            }),
        );
        const store = useHistoryStore();
        const creating = store.createNewHistory(name);
        await flushPromises();
        const switching = store.setCurrentHistory("other-history");
        await flushPromises();
        const beforeRelease = [...requested];
        releaseCreate();
        await Promise.all([creating, switching]);

        expect(beforeRelease).toEqual(["create"]);
        expect(requested).toEqual(["create", "select other-history"]);
        expect(store.currentHistoryId).toBe("other-history");
        expect(store.changingCurrentHistory).toBe(false);
    });

    it("continues with creation after a queued switch fails", async () => {
        server.use(
            rawHttp.get("/history/set_as_current", () =>
                HttpResponse.json({ err_msg: "switch failed" }, { status: 500 }),
            ),
        );
        const store = useHistoryStore();
        const switching = store.setCurrentHistory("other-history");
        const rejected = expect(switching).rejects.toThrow("switch failed");
        const creating = store.createNewHistory("RNA run");
        await rejected;
        await creating;

        expect(store.currentHistoryId).toBe("named-history");
        expect(store.changingCurrentHistory).toBe(false);
    });

    it("still switches to a named history when the count refresh fails", async () => {
        server.use(
            http.get("/api/histories/count", ({ response }) =>
                response("5XX").json({ err_msg: "count is down", err_code: 500 }, { status: 500 }),
            ),
        );
        const store = useHistoryStore();

        await expect(store.createNewHistory("RNA run")).resolves.toBeUndefined();

        expect(requested).toEqual(["create RNA run"]);
        expect(store.currentHistoryId).toBe("named-history");
    });
});

describe("filling the own-history cache beside the paginated list", () => {
    const summaries = [
        { id: "h1", name: "one", update_time: "2026-01-02T00:00:00" },
        { id: "h2", name: "two", update_time: "2026-01-01T00:00:00" },
    ];
    let requestedLimits: string[];
    let releaseCacheFill: () => void;
    let cacheFillPending: Promise<void>;

    beforeEach(() => {
        setupTestPinia();
        requestedLimits = [];
        cacheFillPending = new Promise<void>((resolve) => {
            releaseCacheFill = resolve;
        });
        server.use(
            http.get("/api/histories", async ({ request, response }) => {
                const limit = new URL(request.url).searchParams.get("limit");
                requestedLimits.push(String(limit));
                // Hold the cache request open while the paginated list loads.
                if (limit === "25") {
                    await cacheFillPending;
                }
                return response.untyped(HttpResponse.json(summaries));
            }),
            http.get("/api/histories/count", ({ response }) => response(200).json(40)),
        );
    });

    it("preserves the scroll offset when filling the cache", async () => {
        const store = useHistoryStore();
        store.historiesOffset = 10;

        const filling = store.fetchOwnHistories({ limit: 25 });
        releaseCacheFill();
        await filling;

        expect(store.historiesOffset).toBe(10);
        expect(store.histories.map((history) => history.id)).toContain("h1");
    });

    it("loads a paginated page while a cache fill is pending", async () => {
        const store = useHistoryStore();

        const filling = store.fetchOwnHistories({ limit: 25 });
        await store.loadHistories(true);
        releaseCacheFill();
        await filling;

        expect(requestedLimits).toContain("10");
    });

    it("marks the own listing loaded only after an unfiltered cache fill", async () => {
        const store = useHistoryStore();
        releaseCacheFill();

        await store.fetchOwnHistories({ search: "name-contains=h1", limit: 25 });
        expect(store.hasLoadedOwnHistories).toBe(false);

        await store.fetchOwnHistories({ limit: 25 });
        expect(store.hasLoadedOwnHistories).toBe(true);
    });

    it("marks the own listing loaded when pagination reaches a partial page", async () => {
        const fullPage = Array.from({ length: 10 }, (_, index) => ({
            id: `p${index}`,
            name: `page ${index}`,
            update_time: "2026-01-03T00:00:00",
        }));
        server.use(http.get("/api/histories", ({ response }) => response.untyped(HttpResponse.json(fullPage))));
        const store = useHistoryStore();

        await store.loadHistories(true);
        expect(store.hasLoadedOwnHistories).toBe(false);

        server.use(http.get("/api/histories", ({ response }) => response.untyped(HttpResponse.json(summaries))));
        await store.loadHistories(true);
        expect(store.hasLoadedOwnHistories).toBe(true);
    });

    it("shares identical concurrent cache fills", async () => {
        const store = useHistoryStore();
        const first = store.fetchOwnHistories({ limit: 25 });
        const second = store.fetchOwnHistories({ limit: 25 });
        releaseCacheFill();
        await Promise.all([first, second]);

        expect(requestedLimits).toEqual(["25"]);
        expect(store.histories.map((history) => history.id)).toEqual(["h1", "h2"]);
    });

    it("retries an identical cache fill after rejection", async () => {
        let attempts = 0;
        server.use(
            http.get("/api/histories", ({ response }) => {
                if (++attempts === 1) {
                    return response("5XX").json({ err_msg: "listing failed", err_code: 500 }, { status: 500 });
                }
                return response.untyped(HttpResponse.json(summaries));
            }),
        );
        const store = useHistoryStore();
        await expect(store.fetchOwnHistories({ limit: 25 })).rejects.toThrow("listing failed");
        await store.fetchOwnHistories({ limit: 25 });

        expect(attempts).toBe(2);
        expect(store.histories.map((history) => history.id)).toEqual(["h1", "h2"]);
    });
});

describe("history loading failures during user initialization", () => {
    beforeEach(() => {
        setupTestPinia();
        vi.spyOn(userQueries, "getCurrentUser").mockResolvedValue(null);
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it.each([1, 2])("allows retry after history count request %i fails", async (failedRequest) => {
        let countRequests = 0;
        const listRequest = vi.fn();
        server.use(
            rawHttp.get("/api/histories/count", () => {
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
        server.use(rawHttp.get("/api/histories/count", () => HttpResponse.error()));
        const userStore = useUserStore();
        await expect(userStore.loadUser()).rejects.toThrow();
        await expect(userStore.loadUser(false)).resolves.toBeUndefined();
        expect(userQueries.getCurrentUser).toHaveBeenCalledTimes(2);
    });
});

describe("loading a single history", () => {
    beforeEach(() => {
        setupTestPinia();
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("loads the history on a later lookup after a request fails to reach the server", async () => {
        const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
        server.use(rawHttp.get("/api/histories/:history_id", () => HttpResponse.error()));
        const historyStore = useHistoryStore();

        expect(historyStore.getHistoryById("history-1")).toBeNull();
        await vi.waitFor(() => expect(warn).toHaveBeenCalled());
        await flushPromises();
        expect(historyStore.getHistoryLoadError("history-1")).toBeInstanceOf(Error);

        server.use(
            rawHttp.get("/api/histories/:history_id", () =>
                HttpResponse.json({ id: "history-1", name: "Test history" }),
            ),
        );
        historyStore.getHistoryById("history-1");
        await vi.waitFor(() => expect(historyStore.getHistoryById("history-1")?.name).toBe("Test history"));
        expect(historyStore.getHistoryLoadError("history-1")).toBeNull();
    });

    it("stops retrying a history that keeps failing to reach the server", async () => {
        vi.spyOn(console, "warn").mockImplementation(() => {});
        let requests = 0;
        server.use(
            rawHttp.get("/api/histories/:history_id", () => {
                requests += 1;
                return HttpResponse.error();
            }),
        );
        const historyStore = useHistoryStore();

        for (let i = 0; i < 10; i++) {
            historyStore.getHistoryById("history-1");
            await flushPromises();
            await vi.waitFor(() => expect(historyStore.getHistoryLoadError("history-1")).toBeInstanceOf(Error));
        }
        expect(requests).toBe(MAX_RETRIES + 1);
    });

    it("rejects and records an awaited load that fails to reach the server", async () => {
        server.use(rawHttp.get("/api/histories/:history_id", () => HttpResponse.error()));
        const historyStore = useHistoryStore();

        await expect(historyStore.loadHistoryById("history-1")).rejects.toThrow();
        expect(historyStore.getHistoryLoadError("history-1")).toBeInstanceOf(Error);
    });
});
