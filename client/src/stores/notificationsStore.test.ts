import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { useServerMock } from "@/api/client/__mocks__";
import type { UserNotification } from "@/api/notifications";

import { useNotificationsStore } from "./notificationsStore";

// Capture SSE composable usage without opening a real EventSource.
// The returned `connected` ref stays false by default — this is intentional
// because the store must NOT be relying on it; the decision is config-driven.
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
        content: { subject: "hello", message: "welcome" },
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

function configResponse(overrides: Record<string, unknown>) {
    // The /api/configuration response carries many fields; the store only
    // reads enable_notification_system, so a minimal object suffices.
    return { enable_notification_system: false, ...overrides };
}

function registerDefaultHandlers({ enableNotificationSystem }: { enableNotificationSystem: boolean }) {
    server.use(
        http.get("/api/configuration", ({ response }) => {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            return response(200).json(configResponse({ enable_notification_system: enableNotificationSystem }) as any);
        }),
        http.get("/api/notifications", ({ response }) => {
            return response(200).json([SCENARIO_NOTIFICATION]);
        }),
        http.get("/api/notifications/broadcast", ({ response }) => {
            return response(200).json([]);
        }),
        http.get("/api/notifications/status", ({ response }) => {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            return response(200).json(SCENARIO_STATUS_SINCE as any);
        }),
    );
}

describe("notificationsStore — config-driven SSE vs polling", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        mockSseConnect.mockClear();
        mockSseDisconnect.mockClear();
        mockSseConnected.value = false;
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    describe("when enable_notification_system is true (SSE scenario)", () => {
        beforeEach(() => {
            registerDefaultHandlers({ enableNotificationSystem: true });
        });

        it("connects SSE and does not poll the status endpoint", async () => {
            const store = useNotificationsStore();

            // The store fires an initial load (GET /api/notifications + broadcasts)
            // and then decides SSE vs polling based on the config flag.
            const statusSpy = vi.fn();
            server.use(
                http.get("/api/notifications/status", ({ response }) => {
                    statusSpy();
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    return response(200).json(SCENARIO_STATUS_SINCE as any);
                }),
            );

            await vi.runOnlyPendingTimersAsync();
            await store.startWatchingNotifications();
            await flushPromises();

            // The config load is async — let the watch fire.
            await vi.runOnlyPendingTimersAsync();
            await flushPromises();

            expect(mockSseConnect).toHaveBeenCalledTimes(1);

            // Advance well past the polling interval (30s) and confirm
            // the status endpoint is never polled while SSE is the active channel.
            vi.advanceTimersByTime(120_000);
            await flushPromises();
            expect(statusSpy).not.toHaveBeenCalled();
        });

        it("does not start polling when the tab regains visibility", async () => {
            const store = useNotificationsStore();
            const statusSpy = vi.fn();
            server.use(
                http.get("/api/notifications/status", ({ response }) => {
                    statusSpy();
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    return response(200).json(SCENARIO_STATUS_SINCE as any);
                }),
            );

            await vi.runOnlyPendingTimersAsync();
            await store.startWatchingNotifications();
            await flushPromises();
            await vi.runOnlyPendingTimersAsync();
            await flushPromises();

            // Tab hide/show cycle — must not trigger the status endpoint.
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
            vi.advanceTimersByTime(120_000);
            await flushPromises();
            expect(statusSpy).not.toHaveBeenCalled();
        });
    });

    describe("when enable_notification_system is false (polling scenario)", () => {
        beforeEach(() => {
            registerDefaultHandlers({ enableNotificationSystem: false });
        });

        it("does not connect SSE and polls the status endpoint on the configured interval", async () => {
            const store = useNotificationsStore();

            const statusSpy = vi.fn();
            server.use(
                http.get("/api/notifications/status", ({ response }) => {
                    statusSpy();
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    return response(200).json(SCENARIO_STATUS_SINCE as any);
                }),
            );

            await vi.runOnlyPendingTimersAsync();
            await store.startWatchingNotifications();
            await flushPromises();
            await vi.runOnlyPendingTimersAsync();
            await flushPromises();

            expect(mockSseConnect).not.toHaveBeenCalled();

            // Advance past the short polling interval (30s) and confirm
            // the status endpoint is hit by the resource watcher.
            vi.advanceTimersByTime(30_000);
            await flushPromises();
            expect(statusSpy).toHaveBeenCalled();
        });
    });
});
