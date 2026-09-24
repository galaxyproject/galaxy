/**
 * Unit tests for the viewer-subscription helpers in useNotificationSSE.
 *
 * The shared EventSource isn't exercised here — these tests focus on the
 * client-side bookkeeping: refcounting, dedup, and HTTP shape. Reconnect
 * replay is covered by an MSW request log assertion plus an explicit call
 * into the (test-only) onopen replay path.
 */

import flushPromises from "flush-promises";
import { http, HttpResponse } from "msw";
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
        const recordHandler = async ({ request }: { request: Request }) => {
            const body = (await request.json()) as { history_ids: string[] };
            requests.push({
                method: request.method as "POST" | "DELETE",
                history_ids: body.history_ids,
            });
            return new HttpResponse(null, { status: 204 });
        };
        server.use(
            http.post("/api/events/history-subscriptions", recordHandler),
            http.delete("/api/events/history-subscriptions", recordHandler),
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
        expect(requests.filter((r) => r.method === "POST")).toHaveLength(1);
    });

    it("only DELETEs when the last subscriber for an id releases", async () => {
        addHistoryViewerSubscription("hist-A");
        addHistoryViewerSubscription("hist-A");
        await flushPromises();
        const postCount = requests.filter((r) => r.method === "POST").length;

        removeHistoryViewerSubscription("hist-A");
        await flushPromises();
        // First remove still has one outstanding refcount — must not DELETE yet.
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

/**
 * Reconnect-on-CLOSED tests.
 *
 * The browser's native ``EventSource`` retries while ``readyState ===
 * CONNECTING`` but gives up once it flips to ``CLOSED`` — for example, when a
 * 429/5xx response arrives without ``text/event-stream``. The composable must
 * notice that flip and schedule a manual reopen with backoff so the client
 * doesn't silently drop to polling-only updates for the rest of the session.
 *
 * We stub ``globalThis.EventSource`` with a fake whose lifecycle the test
 * drives directly: this keeps the test off jsdom's ``EventSource`` (which
 * doesn't actually open sockets) and gives us a deterministic handle on the
 * instance count for the "a *new* EventSource was constructed after backoff"
 * assertion.
 */
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

describe("useNotificationSSE managed reconnect", () => {
    let originalEventSource: typeof EventSource | undefined;
    // ``useSSE`` registers an ``onScopeDispose`` cleanup; outside a Vue
    // component setup that warns and ``vitest-fail-on-console`` upgrades the
    // warning to a test failure. Wrap each test in an explicit scope so the
    // disposal hook has somewhere to attach.
    let scope: EffectScope;

    beforeEach(() => {
        FakeEventSource.reset();
        originalEventSource = (globalThis as unknown as { EventSource?: typeof EventSource }).EventSource;
        (globalThis as unknown as { EventSource: unknown }).EventSource = FakeEventSource;
        vi.useFakeTimers();
        _resetSSESharedSourceForTest();
        scope = effectScope();
    });

    afterEach(() => {
        scope.stop();
        vi.useRealTimers();
        _resetSSESharedSourceForTest();
        if (originalEventSource) {
            (globalThis as unknown as { EventSource: typeof EventSource }).EventSource = originalEventSource;
        } else {
            delete (globalThis as unknown as { EventSource?: unknown }).EventSource;
        }
    });

    it("schedules a reopen when onerror fires with readyState=CLOSED", () => {
        scope.run(() => {
            const { connect } = useSSE(() => {});
            connect();
        });
        expect(FakeEventSource.instances).toHaveLength(1);

        const first = FakeEventSource.instances[0]!;
        // Simulate the browser giving up on the native retry.
        first.readyState = FakeEventSource.CLOSED;
        first.onerror?.();

        // Until the backoff fires, no replacement EventSource exists yet.
        expect(FakeEventSource.instances).toHaveLength(1);

        // The first attempt's backoff is in [500ms, 1500ms); 2000ms is past
        // the upper bound regardless of the jitter draw, so a fixed advance
        // is deterministic without seeding ``Math.random``.
        vi.advanceTimersByTime(2000);
        expect(FakeEventSource.instances).toHaveLength(2);
    });

    it("does not reopen while readyState=CONNECTING (browser is still retrying natively)", () => {
        scope.run(() => {
            const { connect } = useSSE(() => {});
            connect();
        });
        const first = FakeEventSource.instances[0]!;
        first.readyState = FakeEventSource.CONNECTING;
        first.onerror?.();

        // No manual scheduling while the browser is still trying — would
        // otherwise double-up reconnect work and accelerate the retry loop.
        // A full minute past any backoff envelope without a second instance
        // proves the managed path stayed dormant.
        vi.advanceTimersByTime(60_000);
        expect(FakeEventSource.instances).toHaveLength(1);
    });

    it("resets the backoff counter on a successful onopen", () => {
        scope.run(() => {
            const { connect } = useSSE(() => {});
            connect();
        });

        // Stack five back-to-back failures so the unjittered base delay grows
        // to the 30s cap. After this loop the next attempt's envelope is
        // [15s, 45s) — well outside the [500ms, 1500ms) envelope a freshly
        // reset counter would produce. ``45_001`` clears the worst-case jitter
        // draw on each iteration so the timer always fires.
        const STACKED = 5;
        for (let i = 0; i < STACKED; i++) {
            const current = FakeEventSource.instances.at(-1)!;
            current.readyState = FakeEventSource.CLOSED;
            current.onerror?.();
            vi.advanceTimersByTime(45_001);
        }
        const beforeReset = FakeEventSource.instances.length;
        expect(beforeReset).toBe(STACKED + 1);

        // Trigger a sixth failure and verify the *capped* envelope: a 2s
        // advance is below the 15s lower bound, so no new instance appears.
        // Without this assertion the reset test below would pass even if the
        // counter never reset, since both paths would fire on a 2s advance.
        const stale = FakeEventSource.instances.at(-1)!;
        stale.readyState = FakeEventSource.CLOSED;
        stale.onerror?.();
        vi.advanceTimersByTime(2000);
        expect(FakeEventSource.instances).toHaveLength(beforeReset);

        // Drain the in-flight capped timer so we have a fresh source whose
        // ``onopen`` will reset the counter.
        vi.advanceTimersByTime(45_001);
        expect(FakeEventSource.instances).toHaveLength(beforeReset + 1);
        const reopened = FakeEventSource.instances.at(-1)!;
        reopened.onopen?.();

        // Counter reset → next failure's delay drops back to [500, 1500); a
        // 2s advance must fire it.
        reopened.readyState = FakeEventSource.CLOSED;
        reopened.onerror?.();
        vi.advanceTimersByTime(2000);
        expect(FakeEventSource.instances).toHaveLength(beforeReset + 2);
    });
});

/**
 * Forced-reconnect tests.
 *
 * Background tabs throttle/suspend the timers both the browser's native retry
 * and the managed backoff depend on, so a drop while hidden can sit
 * un-recovered. ``reconnectSSE`` (the "click to refresh" affordance) and the
 * wake/online listeners must reopen immediately, ignoring the backoff
 * schedule, and only when a connection is actually wanted/lost.
 */
describe("useNotificationSSE forced reconnect", () => {
    let originalEventSource: typeof EventSource | undefined;
    let scope: EffectScope;

    beforeEach(() => {
        FakeEventSource.reset();
        originalEventSource = (globalThis as unknown as { EventSource?: typeof EventSource }).EventSource;
        (globalThis as unknown as { EventSource: unknown }).EventSource = FakeEventSource;
        vi.useFakeTimers();
        _resetSSESharedSourceForTest();
        scope = effectScope();
    });

    afterEach(() => {
        scope.stop();
        vi.useRealTimers();
        _resetSSESharedSourceForTest();
        if (originalEventSource) {
            (globalThis as unknown as { EventSource: typeof EventSource }).EventSource = originalEventSource;
        } else {
            delete (globalThis as unknown as { EventSource?: unknown }).EventSource;
        }
    });

    it("reconnectSSE reopens immediately without waiting for backoff", () => {
        scope.run(() => {
            const { connect } = useSSE(() => {});
            connect();
        });
        expect(FakeEventSource.instances).toHaveLength(1);

        const first = FakeEventSource.instances[0]!;
        first.readyState = FakeEventSource.CLOSED;
        first.onerror?.();
        // A managed reopen is now armed, but reconnectSSE should not wait for it.
        reconnectSSE();
        expect(FakeEventSource.instances).toHaveLength(2);

        // The armed backoff timer was cancelled, so advancing time does not
        // spawn a third instance.
        vi.advanceTimersByTime(60_000);
        expect(FakeEventSource.instances).toHaveLength(2);
    });

    it("reconnectSSE resets the backoff so the next failure starts at the base envelope", () => {
        scope.run(() => {
            const { connect } = useSSE(() => {});
            connect();
        });

        // Stack failures to drive the unjittered delay to the 30s cap.
        const STACKED = 5;
        for (let i = 0; i < STACKED; i++) {
            const current = FakeEventSource.instances.at(-1)!;
            current.readyState = FakeEventSource.CLOSED;
            current.onerror?.();
            vi.advanceTimersByTime(45_001);
        }
        const beforeReconnect = FakeEventSource.instances.length;

        // Forced reconnect opens now and zeroes the counter.
        reconnectSSE();
        expect(FakeEventSource.instances).toHaveLength(beforeReconnect + 1);

        // Next failure must fire on the base [500, 1500) envelope — a 2s
        // advance proves the counter reset (the capped path would need ~15s).
        const reopened = FakeEventSource.instances.at(-1)!;
        reopened.readyState = FakeEventSource.CLOSED;
        reopened.onerror?.();
        vi.advanceTimersByTime(2000);
        expect(FakeEventSource.instances).toHaveLength(beforeReconnect + 2);
    });

    it("reconnectSSE is a no-op when there are no subscribers", () => {
        // No connect() — the subscriber map is empty.
        reconnectSSE();
        expect(FakeEventSource.instances).toHaveLength(0);
    });

    it("reconnects when the tab becomes visible again while disconnected", () => {
        scope.run(() => {
            const { connect } = useSSE(() => {});
            connect();
        });
        const first = FakeEventSource.instances[0]!;
        first.onopen?.();
        // Connection drops while backgrounded.
        first.readyState = FakeEventSource.CLOSED;
        first.onerror?.();

        document.dispatchEvent(new Event("visibilitychange"));
        // jsdom reports ``document.visibilityState === "visible"`` by default,
        // so the wake handler should fire an immediate reopen.
        expect(FakeEventSource.instances).toHaveLength(2);
    });

    it("does not reconnect on visibilitychange while the connection is healthy", () => {
        scope.run(() => {
            const { connect } = useSSE(() => {});
            connect();
        });
        const first = FakeEventSource.instances[0]!;
        first.onopen?.();

        document.dispatchEvent(new Event("visibilitychange"));
        expect(FakeEventSource.instances).toHaveLength(1);
    });

    it("reconnects when network connectivity returns while disconnected", () => {
        scope.run(() => {
            const { connect } = useSSE(() => {});
            connect();
        });
        const first = FakeEventSource.instances[0]!;
        first.onopen?.();
        first.readyState = FakeEventSource.CLOSED;
        first.onerror?.();

        window.dispatchEvent(new Event("online"));
        expect(FakeEventSource.instances).toHaveLength(2);
    });
});
