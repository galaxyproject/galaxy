import { getFakeRegisteredUser } from "@tests/test-data";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { AnonymousUser } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";

import { emitSse, setSseConnected, sseMockFactory, useVisibilityPatch } from "./_testing/sseStoreSupport";
import { useUserStore } from "./userStore";

// ``vi.mock`` is hoisted above module-level ``const`` declarations, so the
// capture-state has to be built via ``vi.hoisted`` to be visible to the factory.
const sseState = vi.hoisted(() => ({
    onEvent: null as ((event: MessageEvent) => void) | null,
    connect: vi.fn(),
    disconnect: vi.fn(),
}));

vi.mock("@/composables/useNotificationSSE", () => sseMockFactory(sseState));

const { server, http } = useServerMock();

describe("userStore — watching the storage usage", () => {
    let userRequests: number;
    let visibility: ReturnType<typeof useVisibilityPatch>;

    async function startWatching({ enableSse }: { enableSse: boolean }) {
        server.use(
            http.get("/api/configuration", ({ response }) => {
                return response(200).json({
                    enable_sse_updates: enableSse,
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                } as any);
            }),
        );
        await useUserStore().startWatchingStorageUsage();
        await flushPromises();
    }

    beforeEach(() => {
        setActivePinia(createPinia());
        vi.useFakeTimers();
        visibility = useVisibilityPatch();
        sseState.connect.mockClear();
        setSseConnected(sseState, false);
        userRequests = 0;
        server.use(
            http.get("/api/users/{user_id}", ({ response }) => {
                userRequests++;
                return response(200).json(getFakeRegisteredUser());
            }),
        );
    });

    async function returnToTab() {
        visibility.set("hidden");
        await flushPromises();
        visibility.set("visible");
        await flushPromises();
    }

    afterEach(() => {
        useUserStore().$dispose();
        visibility.restore();
        vi.useRealTimers();
        vi.restoreAllMocks();
    });

    describe("with live updates", () => {
        it("refreshes the user when the server reports a quota change", async () => {
            await startWatching({ enableSse: true });

            emitSse(sseState, "user_quota_update", {});
            await flushPromises();

            expect(sseState.connect).toHaveBeenCalledTimes(1);
            expect(userRequests).toBe(1);
        });

        it("refreshes at most once per window while changes keep coming", async () => {
            await startWatching({ enableSse: true });

            emitSse(sseState, "user_quota_update", {});
            emitSse(sseState, "user_quota_update", {});
            emitSse(sseState, "user_quota_update", {});
            await flushPromises();
            expect(userRequests).toBe(1);

            // The last change still arrives once the window ends
            await vi.advanceTimersByTimeAsync(5000);
            expect(userRequests).toBe(2);
        });

        it("spreads out the refresh after a change concerning every user", async () => {
            vi.spyOn(Math, "random").mockReturnValue(0.5);
            await startWatching({ enableSse: true });

            emitSse(sseState, "user_quota_update", { broadcast: true });
            await vi.advanceTimersByTimeAsync(14_000);
            expect(userRequests).toBe(0);

            await vi.advanceTimersByTimeAsync(1000);
            expect(userRequests).toBe(1);
        });

        it("refreshes once after several changes concerning every user in a row", async () => {
            vi.spyOn(Math, "random").mockReturnValue(0.5);
            await startWatching({ enableSse: true });

            emitSse(sseState, "user_quota_update", { broadcast: true });
            await vi.advanceTimersByTimeAsync(10_000);
            emitSse(sseState, "user_quota_update", { broadcast: true });
            await vi.advanceTimersByTimeAsync(30_000);

            expect(userRequests).toBe(1);
        });

        it("refreshes after reconnecting, since changes sent meanwhile were missed, spread out over time", async () => {
            vi.spyOn(Math, "random").mockReturnValue(0.5);
            await startWatching({ enableSse: true });

            setSseConnected(sseState, true);
            await flushPromises();
            expect(userRequests).toBe(0);

            setSseConnected(sseState, false);
            await flushPromises();
            setSseConnected(sseState, true);
            await vi.advanceTimersByTimeAsync(4000);
            expect(userRequests).toBe(0);

            await vi.advanceTimersByTimeAsync(1000);
            expect(userRequests).toBe(1);
        });

        it("refreshes once when the user returns to a tab whose live updates dropped while hidden", async () => {
            await startWatching({ enableSse: true });
            setSseConnected(sseState, true);
            await flushPromises();

            visibility.set("hidden");
            setSseConnected(sseState, false);
            await flushPromises();
            visibility.set("visible");
            await flushPromises();
            expect(userRequests).toBe(0);

            // Returning to the tab reconnects live updates, which catches up at once
            setSseConnected(sseState, true);
            await flushPromises();
            expect(userRequests).toBe(1);

            await vi.advanceTimersByTimeAsync(60_000);
            expect(userRequests).toBe(1);
        });

        it("refreshes anyway when live updates don't reconnect after the user returns", async () => {
            await startWatching({ enableSse: true });
            setSseConnected(sseState, true);
            await flushPromises();

            visibility.set("hidden");
            setSseConnected(sseState, false);
            await flushPromises();
            visibility.set("visible");
            await vi.advanceTimersByTimeAsync(9000);
            expect(userRequests).toBe(0);

            await vi.advanceTimersByTimeAsync(1000);
            expect(userRequests).toBe(1);
        });

        it("still refreshes when the user returns to the tab, for changes made outside Galaxy's code", async () => {
            await startWatching({ enableSse: true });
            setSseConnected(sseState, true);
            await flushPromises();

            await returnToTab();

            expect(userRequests).toBe(1);
        });
    });

    describe("without live updates", () => {
        it("refreshes when the user returns to the tab, at most once a minute", async () => {
            await startWatching({ enableSse: false });

            await returnToTab();
            expect(userRequests).toBe(1);

            await returnToTab();
            expect(userRequests).toBe(1);

            await vi.advanceTimersByTimeAsync(61_000);
            await returnToTab();
            expect(userRequests).toBe(2);
            expect(sseState.connect).not.toHaveBeenCalled();
        });
    });

    const ANONYMOUS_USER: AnonymousUser = { isAnonymous: true, total_disk_usage: 0, nice_total_disk_usage: "0 bytes" };

    it.each([
        {
            title: "leaves a usage change to the server's event while live updates are connected",
            enableSse: true,
            connected: true,
            user: getFakeRegisteredUser(),
            requests: 0,
        },
        {
            title: "refreshes after a usage change while live updates are disconnected",
            enableSse: true,
            connected: false,
            user: getFakeRegisteredUser(),
            requests: 1,
        },
        {
            title: "refreshes after a usage change without live updates",
            enableSse: false,
            connected: false,
            user: getFakeRegisteredUser(),
            requests: 1,
        },
        {
            title: "refreshes after an anonymous user's usage change, which the server doesn't announce",
            enableSse: true,
            connected: true,
            user: ANONYMOUS_USER,
            requests: 1,
        },
    ])("$title", async ({ enableSse, connected, user, requests }) => {
        const userStore = useUserStore();
        userStore.currentUser = user;
        await startWatching({ enableSse });
        setSseConnected(sseState, connected);
        await flushPromises();

        userStore.refreshStorageUsageUnlessLive();
        await flushPromises();

        expect(userRequests).toBe(requests);
    });

    it("refreshes when the user returns to the tab even if the configuration fails to load", async () => {
        server.use(
            http.get("/api/configuration", ({ response }) => {
                return response("5XX").json({ err_msg: "Server error", err_code: 500 }, { status: 500 });
            }),
        );
        vi.spyOn(console, "error").mockImplementation(() => {});
        // Never resolves here: it waits for the configuration to connect to live updates
        void useUserStore().startWatchingStorageUsage();
        await flushPromises();

        await returnToTab();

        expect(userRequests).toBe(1);
        expect(sseState.connect).not.toHaveBeenCalled();
    });

    it("holds changes back while the tab is hidden and refreshes as soon as the user returns", async () => {
        await startWatching({ enableSse: false });
        await returnToTab();
        expect(userRequests).toBe(1);

        visibility.set("hidden");
        await flushPromises();
        useUserStore().refreshStorageUsageUnlessLive();
        await flushPromises();
        expect(userRequests).toBe(1);

        // Within a minute of the last refresh on return, which would otherwise skip this one
        visibility.set("visible");
        await flushPromises();
        expect(userRequests).toBe(2);
    });
});
