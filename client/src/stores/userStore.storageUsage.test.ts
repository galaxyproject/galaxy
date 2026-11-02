import { getFakeRegisteredUser } from "@tests/test-data";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import { useVisibilityPatch } from "./_testing/sseStoreSupport";
import { useUserStore } from "./userStore";

const { server, http } = useServerMock();

describe("userStore — watching the storage usage", () => {
    let userRequests: number;
    let visibility: ReturnType<typeof useVisibilityPatch>;

    beforeEach(() => {
        setActivePinia(createPinia());
        vi.useFakeTimers();
        visibility = useVisibilityPatch();
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
    });

    it("refreshes when the user returns to the tab, at most once a minute", async () => {
        useUserStore().startWatchingStorageUsage();

        await returnToTab();
        expect(userRequests).toBe(1);

        await returnToTab();
        expect(userRequests).toBe(1);

        await vi.advanceTimersByTimeAsync(61_000);
        await returnToTab();
        expect(userRequests).toBe(2);
    });

    it("holds changes back while the tab is hidden and refreshes as soon as the user returns", async () => {
        useUserStore().startWatchingStorageUsage();
        await returnToTab();
        expect(userRequests).toBe(1);

        visibility.set("hidden");
        await flushPromises();
        useUserStore().refreshStorageUsageThrottled();
        await flushPromises();
        expect(userRequests).toBe(1);

        // Within a minute of the last refresh on return, which would otherwise skip this one
        visibility.set("visible");
        await flushPromises();
        expect(userRequests).toBe(2);
    });
});
