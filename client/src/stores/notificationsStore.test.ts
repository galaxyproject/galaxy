import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import type { components } from "@/api/schema";
import { generateMessageNotification } from "@/components/Notifications/test-utils";

import { emitSse, sseMockFactory, trackVisibilityListeners, useVisibilityPatch } from "./_testing/sseStoreSupport";
import { useNotificationsStore } from "./notificationsStore";
import { setupTestPinia } from "./testUtils";

const sseState = vi.hoisted(() => {
    return {
        onEvent: null as ((event: MessageEvent) => void) | null,
        connect: vi.fn(),
        disconnect: vi.fn(),
    };
});

vi.mock("@/composables/useNotificationSSE", () => sseMockFactory(sseState));

const initialNotification = generateMessageNotification({
    id: "notif-1",
    source: "galaxy_test",
    create_time: "2026-01-01T00:00:00",
    update_time: "2026-01-01T00:00:00",
    publication_time: "2026-01-01T00:00:00",
    expiration_time: null,
    content: { subject: "hello", message: "welcome" },
});
const initialStatus = {
    total_unread_count: 1,
    notifications: [initialNotification],
    broadcasts: [],
} satisfies components["schemas"]["NotificationStatusSummary"];

const { server, http } = useServerMock();

const statusSpy = vi.fn();

function registerHandlers(enableSseUpdates: boolean) {
    server.use(
        http.get("/api/configuration", ({ response }) => {
            return response.untyped(
                HttpResponse.json({
                    enable_notification_system: true,
                    enable_sse_updates: enableSseUpdates,
                }),
            );
        }),
        http.get("/api/notifications", ({ response }) => {
            return response(200).json([initialNotification]);
        }),
        http.get("/api/notifications/broadcast", ({ response }) => {
            return response(200).json([]);
        }),
        http.get("/api/notifications/status", ({ response }) => {
            statusSpy();
            return response(200).json(initialStatus);
        }),
    );
}

/** Config load + initial fetch + store-decision watch needs a couple of ticks. */
async function startWatching(store: ReturnType<typeof useNotificationsStore>): Promise<void> {
    // Let the config-store fetch resolve before the store's `watch` runs.
    await vi.runOnlyPendingTimersAsync();
    await store.startWatchingNotifications();
    // Two flush cycles: one for the config watch, one for the resulting fetch.
    await flushPromises();
    await vi.runOnlyPendingTimersAsync();
    await flushPromises();
}

describe("notificationsStore — config-driven SSE vs polling", () => {
    let visibility: ReturnType<typeof useVisibilityPatch>;
    let visibilityListeners: ReturnType<typeof trackVisibilityListeners>;

    beforeEach(() => {
        setupTestPinia();
        sseState.connect.mockClear();
        sseState.disconnect.mockClear();
        sseState.onEvent = null;
        statusSpy.mockClear();
        vi.useFakeTimers();
        visibility = useVisibilityPatch();
        visibility.set("visible");
        visibilityListeners = trackVisibilityListeners();
    });

    afterEach(() => {
        useNotificationsStore().stopWatchingNotifications();
        useNotificationsStore().$dispose();
        visibilityListeners.restore();
        visibility.restore();
        vi.useRealTimers();
    });

    describe("when enable_sse_updates is true (SSE scenario)", () => {
        beforeEach(() => {
            registerHandlers(true);
        });

        it("connects SSE and does not poll the status endpoint", async () => {
            const store = useNotificationsStore();
            await startWatching(store);

            expect(sseState.connect).toHaveBeenCalledTimes(1);

            // Advance well past the polling interval (30s) and confirm
            // the status endpoint is never polled while SSE is the active channel.
            vi.advanceTimersByTime(120_000);
            await flushPromises();
            expect(statusSpy).not.toHaveBeenCalled();
        });

        it("does not start polling when the tab regains visibility", async () => {
            const store = useNotificationsStore();
            await startWatching(store);

            visibility.set("hidden");
            visibility.set("visible");

            await flushPromises();
            vi.advanceTimersByTime(120_000);
            await flushPromises();
            expect(statusSpy).not.toHaveBeenCalled();
        });

        it("ingests notification_update events into the store state", async () => {
            const store = useNotificationsStore();
            await startWatching(store);

            const pushed = generateMessageNotification({
                ...initialNotification,
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
            await startWatching(store);

            emitSse(sseState, "notification_status", {
                total_unread_count: 42,
                notifications: [
                    generateMessageNotification({
                        ...initialNotification,
                        id: "notif-catchup",
                    }),
                ],
                broadcasts: [],
            });
            await flushPromises();

            expect(store.totalUnreadCount).toBe(42);
            expect(store.notifications.map((n) => n.id)).toContain("notif-catchup");
        });
    });

    describe("when enable_sse_updates is false (polling scenario)", () => {
        beforeEach(() => {
            registerHandlers(false);
        });

        it("does not connect SSE and polls the status endpoint on the configured interval", async () => {
            const store = useNotificationsStore();
            await startWatching(store);

            expect(sseState.connect).not.toHaveBeenCalled();

            // Advance past the short polling interval (30s) and confirm
            // the status endpoint is hit by the resource watcher.
            vi.advanceTimersByTime(30_000);
            await flushPromises();
            expect(statusSpy).toHaveBeenCalled();
        });
    });
});
