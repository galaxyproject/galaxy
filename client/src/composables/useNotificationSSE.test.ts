import flushPromises from "flush-promises";
import { http, HttpResponse, type PathParams } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { type EffectScope, effectScope } from "vue";

import { useServerMock } from "@/api/client/__mocks__";

import {
    _resetHistoryViewerSubscriptionsForTest,
    _resetSSESharedSourceForTest,
    addHistoryViewerSubscription,
    reconnectSSE,
    removeHistoryViewerSubscription,
    useSSE,
} from "./useNotificationSSE";

interface SubscriptionRequest {
    method: "POST" | "DELETE";
    history_ids: string[];
}

const { server } = useServerMock();

describe("useNotificationSSE viewer subscriptions", () => {
    let requests: SubscriptionRequest[];

    beforeEach(() => {
        _resetHistoryViewerSubscriptionsForTest();
        requests = [];
        server.use(
            http.post<PathParams, { history_ids: string[] }>(
                "/api/events/history-subscriptions",
                async ({ request }) => {
                    const body = await request.json();
                    requests.push({ method: "POST", history_ids: body.history_ids });
                    return new HttpResponse(null, { status: 204 });
                },
            ),
            http.delete<PathParams, { history_ids: string[] }>(
                "/api/events/history-subscriptions",
                async ({ request }) => {
                    const body = await request.json();
                    requests.push({ method: "DELETE", history_ids: body.history_ids });
                    return new HttpResponse(null, { status: 204 });
                },
            ),
        );
    });

    afterEach(() => {
        _resetHistoryViewerSubscriptionsForTest();
    });

    it("POSTs once per first subscriber for a given history id", async () => {
        addHistoryViewerSubscription("hist-A");
        await flushPromises();
        expect(requests).toHaveLength(1);
        expect(requests[0]?.method).toBe("POST");
        expect(requests[0]?.history_ids).toEqual(["hist-A"]);
    });

    it("refcounts duplicate subscriptions — second add is a no-op on the wire", async () => {
        addHistoryViewerSubscription("hist-A");
        addHistoryViewerSubscription("hist-A");
        await flushPromises();
        expect(requests).toEqual([{ method: "POST", history_ids: ["hist-A"] }]);
    });

    it("only DELETEs when the last subscriber for an id releases", async () => {
        addHistoryViewerSubscription("hist-A");
        addHistoryViewerSubscription("hist-A");
        await flushPromises();
        const postCount = requests.filter((r) => r.method === "POST").length;

        removeHistoryViewerSubscription("hist-A");
        await flushPromises();

        expect(requests.filter((r) => r.method === "DELETE")).toHaveLength(0);
        expect(requests.filter((r) => r.method === "POST")).toHaveLength(postCount);

        removeHistoryViewerSubscription("hist-A");
        await flushPromises();
        const deletes = requests.filter((r) => r.method === "DELETE");
        expect(deletes).toHaveLength(1);
        expect(deletes[0]?.history_ids).toEqual(["hist-A"]);
    });

    it("ignores unsubscribes for ids that were never subscribed", async () => {
        removeHistoryViewerSubscription("hist-never");
        await flushPromises();
        expect(requests).toHaveLength(0);
    });

    it("tracks distinct history ids independently", async () => {
        addHistoryViewerSubscription("hist-A");
        addHistoryViewerSubscription("hist-B");
        await flushPromises();
        const ids = requests.filter((r) => r.method === "POST").map((r) => r.history_ids[0]);
        expect(new Set(ids)).toEqual(new Set(["hist-A", "hist-B"]));
    });
});

class FakeEventSource {
    static CONNECTING = 0;
    static OPEN = 1;
    static CLOSED = 2;
    static instances: FakeEventSource[] = [];

    readonly url: string;
    readyState: number = FakeEventSource.CONNECTING;
    onopen: (() => void) | null = null;
    onerror: (() => void) | null = null;
    onmessage: ((e: MessageEvent) => void) | null = null;
    addEventListener = vi.fn();
    removeEventListener = vi.fn();
    close = vi.fn(() => {
        this.readyState = FakeEventSource.CLOSED;
    });

    constructor(url: string) {
        this.url = url;
        FakeEventSource.instances.push(this);
    }

    static reset() {
        FakeEventSource.instances = [];
    }
}

describe("useNotificationSSE connections", () => {
    let scope: EffectScope;

    beforeEach(() => {
        FakeEventSource.reset();
        vi.stubGlobal("EventSource", FakeEventSource);
        vi.spyOn(document, "visibilityState", "get").mockReturnValue("visible");
        vi.useFakeTimers();
        _resetSSESharedSourceForTest();
        scope = effectScope();
    });

    afterEach(() => {
        scope.stop();
        vi.useRealTimers();
        _resetSSESharedSourceForTest();
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    function connect() {
        scope.run(() => useSSE(() => {}).connect());
    }

    function failConnection(source: FakeEventSource) {
        source.readyState = FakeEventSource.CLOSED;
        source.onerror?.();
    }

    function reachCappedBackoff() {
        // Five failures grow the next delay to [15s, 45s); 45,001ms clears every jitter draw.
        for (let attempt = 0; attempt < 5; attempt++) {
            failConnection(FakeEventSource.instances.at(-1)!);
            vi.advanceTimersByTime(45_001);
        }
    }

    describe("managed reconnect", () => {
        it("schedules a reopen when onerror fires with readyState=CLOSED", () => {
            connect();
            expect(FakeEventSource.instances).toHaveLength(1);

            const first = FakeEventSource.instances[0]!;

            failConnection(first);

            expect(FakeEventSource.instances).toHaveLength(1);

            // The initial jitter envelope is [500ms, 1500ms); 2s always clears it.
            vi.advanceTimersByTime(2000);
            expect(FakeEventSource.instances).toHaveLength(2);
        });

        it("does not reopen while readyState=CONNECTING (browser is still retrying natively)", () => {
            connect();
            const first = FakeEventSource.instances[0]!;
            first.readyState = FakeEventSource.CONNECTING;
            first.onerror?.();

            vi.advanceTimersByTime(60_000);
            expect(FakeEventSource.instances).toHaveLength(1);
        });

        it("resets the backoff counter on a successful onopen", () => {
            connect();

            reachCappedBackoff();
            const beforeReset = FakeEventSource.instances.length;
            expect(beforeReset).toBe(6);

            const stale = FakeEventSource.instances.at(-1)!;
            failConnection(stale);
            vi.advanceTimersByTime(2000);
            expect(FakeEventSource.instances).toHaveLength(beforeReset);

            vi.advanceTimersByTime(45_001);
            expect(FakeEventSource.instances).toHaveLength(beforeReset + 1);
            const reopened = FakeEventSource.instances.at(-1)!;
            reopened.onopen?.();

            failConnection(reopened);
            vi.advanceTimersByTime(2000);
            expect(FakeEventSource.instances).toHaveLength(beforeReset + 2);
        });
    });

    describe("forced reconnect", () => {
        it("reconnectSSE reopens immediately without waiting for backoff", () => {
            connect();
            expect(FakeEventSource.instances).toHaveLength(1);

            const first = FakeEventSource.instances[0]!;
            failConnection(first);

            reconnectSSE();
            expect(FakeEventSource.instances).toHaveLength(2);

            vi.advanceTimersByTime(60_000);
            expect(FakeEventSource.instances).toHaveLength(2);
        });

        it("reconnectSSE resets the backoff so the next failure starts at the base envelope", () => {
            connect();

            reachCappedBackoff();
            const beforeReconnect = FakeEventSource.instances.length;

            reconnectSSE();
            expect(FakeEventSource.instances).toHaveLength(beforeReconnect + 1);

            const reopened = FakeEventSource.instances.at(-1)!;
            failConnection(reopened);
            vi.advanceTimersByTime(2000);
            expect(FakeEventSource.instances).toHaveLength(beforeReconnect + 2);
        });

        it("reconnectSSE is a no-op when there are no subscribers", () => {
            reconnectSSE();
            expect(FakeEventSource.instances).toHaveLength(0);
        });

        it("reconnects when the tab becomes visible again while disconnected", () => {
            connect();
            const first = FakeEventSource.instances[0]!;
            first.onopen?.();

            failConnection(first);

            document.dispatchEvent(new Event("visibilitychange"));

            expect(FakeEventSource.instances).toHaveLength(2);
        });

        it("does not reconnect on visibilitychange while the connection is healthy", () => {
            connect();
            const first = FakeEventSource.instances[0]!;
            first.onopen?.();

            document.dispatchEvent(new Event("visibilitychange"));
            expect(FakeEventSource.instances).toHaveLength(1);
        });

        it("reconnects when network connectivity returns while disconnected", () => {
            connect();
            const first = FakeEventSource.instances[0]!;
            first.onopen?.();
            failConnection(first);

            window.dispatchEvent(new Event("online"));
            expect(FakeEventSource.instances).toHaveLength(2);
        });
    });
});
