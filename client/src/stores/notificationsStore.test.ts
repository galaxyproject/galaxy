import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import type { UserNotification } from "@/api/notifications";

import { emitSse, sseMockFactory, useVisibilityPatch } from "./_testing/sseStoreSupport";
import { useNotificationsStore } from "./notificationsStore";

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

// Realistic fixture: a single unread notification, as returned by
// GET /api/notifications. Shape mirrors UserNotification.
function makeNotificationFixture(overrides: Partial<UserNotification> = {}): UserNotification {
    return {
        id: "notif-1",
        source: "galaxy_test",
        category: "message",
        variant: "info",
        create_time: "2026-01-01T00:00:00",
        update_time: "2026-01-01T00:00:00",
        publication_time: "2026-01-01T00:00:00",
        expiration_time: null,
        seen_time: null,
        deleted: false,
        content: { category: "message", subject: "hello", message: "welcome" },
        ...overrides,
    } as UserNotification;
}

const SCENARIO_NOTIFICATION = makeNotificationFixture();
const SCENARIO_STATUS_SINCE = {
    total_unread_count: 1,
    notifications: [SCENARIO_NOTIFICATION],
    broadcasts: [],
};

const { server, http } = useServerMock();

const statusSpy = vi.fn();

function registerDefaultHandlers({ enableNotificationSystem }: { enableNotificationSystem: boolean }) {
    server.use(
        http.get("/api/configuration", ({ response }) => {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            return response(200).json({ enable_notification_system: enableNotificationSystem } as any);
        }),
        http.get("/api/notifications", ({ response }) => {
            return response(200).json([SCENARIO_NOTIFICATION]);
        }),
        http.get("/api/notifications/broadcast", ({ response }) => {
            return response(200).json([]);
        }),
        http.get("/api/notifications/status", ({ response }) => {
            statusSpy();
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            return response(200).json(SCENARIO_STATUS_SINCE as any);
        }),
    );
}

/** Config load + initial fetch + store-decision watch needs a couple of ticks. */
async function primeStore(startFn: () => Promise<void> | void): Promise<void> {
    // Let the config-store fetch resolve before the store's `watch` runs.
    await vi.runOnlyPendingTimersAsync();
    await startFn();
    // Two flush cycles: one for the config watch, one for the resulting fetch.
    await flushPromises();
    await vi.runOnlyPendingTimersAsync();
    await flushPromises();
}

describe("notificationsStore — config-driven SSE vs polling", () => {
    let visibility: ReturnType<typeof useVisibilityPatch>;

    beforeEach(() => {
        setActivePinia(createPinia());
        sseState.connect.mockClear();
        sseState.disconnect.mockClear();
        sseState.onEvent = null;
        statusSpy.mockClear();
        vi.useFakeTimers();
        visibility = useVisibilityPatch();
    });

    afterEach(() => {
        visibility.restore();
        vi.useRealTimers();
    });

    describe("when enable_notification_system is true (SSE scenario)", () => {
        beforeEach(() => {
            registerDefaultHandlers({ enableNotificationSystem: true });
        });

        it("connects SSE and does not poll the status endpoint", async () => {
            const store = useNotificationsStore();
            await primeStore(() => store.startWatchingNotifications());

            expect(sseState.connect).toHaveBeenCalledTimes(1);

            // Advance well past the polling interval (30s) and confirm
            // the status endpoint is never polled while SSE is the active channel.
            vi.advanceTimersByTime(120_000);
            await flushPromises();
            expect(statusSpy).not.toHaveBeenCalled();
        });

        it("does not start polling when the tab regains visibility", async () => {
            const store = useNotificationsStore();
            await primeStore(() => store.startWatchingNotifications());

            visibility.set("hidden");
            visibility.set("visible");

            await flushPromises();
            vi.advanceTimersByTime(120_000);
            await flushPromises();
            expect(statusSpy).not.toHaveBeenCalled();
        });

        it("ingests notification_update events into the store state", async () => {
            const store = useNotificationsStore();
            await primeStore(() => store.startWatchingNotifications());

            const pushed = makeNotificationFixture({
                id: "notif-2",
                content: { category: "message", subject: "pushed via sse", message: "hi" },
            });
            emitSse(sseState, "notification_update", pushed);
            await flushPromises();

            expect(store.notifications.map((n) => n.id)).toContain("notif-2");
            expect(store.totalUnreadCount).toBeGreaterThan(0);
        });

        it("ingests notification_status catch-up events on reconnect", async () => {
            const store = useNotificationsStore();
            await primeStore(() => store.startWatchingNotifications());

            emitSse(sseState, "notification_status", {
                total_unread_count: 42,
                notifications: [makeNotificationFixture({ id: "notif-catchup" })],
                broadcasts: [],
            });
            await flushPromises();

            expect(store.totalUnreadCount).toBe(42);
            expect(store.notifications.map((n) => n.id)).toContain("notif-catchup");
        });
    });

    describe("when enable_notification_system is false (polling scenario)", () => {
        beforeEach(() => {
            registerDefaultHandlers({ enableNotificationSystem: false });
        });

        it("does not connect SSE and polls the status endpoint on the configured interval", async () => {
            const store = useNotificationsStore();
            await primeStore(() => store.startWatchingNotifications());

            expect(sseState.connect).not.toHaveBeenCalled();

            // Advance past the short polling interval (30s) and confirm
            // the status endpoint is hit by the resource watcher.
            vi.advanceTimersByTime(30_000);
            await flushPromises();
            expect(statusSpy).toHaveBeenCalled();
        });
    });
});
