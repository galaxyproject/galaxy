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
    let sourceUsageRequests: number;
    let visibility: ReturnType<typeof useVisibilityPatch>;

    beforeEach(() => {
        setActivePinia(createPinia());
        vi.useFakeTimers();
        visibility = useVisibilityPatch();
        userRequests = 0;
        sourceUsageRequests = 0;
        server.use(
            http.get("/api/users/{user_id}", ({ response }) => {
                userRequests++;
                return response(200).json(getFakeRegisteredUser());
            }),
            http.get("/api/users/{user_id}/usage", ({ response }) => {
                sourceUsageRequests++;
                return response(200).json([]);
            }),
        );
    });

    async function returnToTab() {
        visibility.set("hidden");
        await flushPromises();
        visibility.set("visible");
        await flushPromises();
    }

    async function startWatchingWithQuotaSources(quotaSourceLabels: string[], { enableQuotas = true } = {}) {
        server.use(
            http.get("/api/configuration", ({ response }) => {
                return response(200).json({
                    enable_quotas: enableQuotas,
                    quota_source_labels: quotaSourceLabels,
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                } as any);
            }),
        );
        useUserStore().startWatchingStorageUsage();
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

    describe("usage of the other storage sources", () => {
        it("is loaded for a registered user on a server with other sources", async () => {
            useUserStore().currentUser = getFakeRegisteredUser();

            await startWatchingWithQuotaSources(["scratch"]);

            expect(sourceUsageRequests).toBe(1);
        });

        it("isn't loaded on a server without other sources", async () => {
            useUserStore().currentUser = getFakeRegisteredUser();

            await startWatchingWithQuotaSources([]);

            expect(sourceUsageRequests).toBe(0);
        });

        it("isn't loaded with quotas off", async () => {
            useUserStore().currentUser = getFakeRegisteredUser();

            await startWatchingWithQuotaSources(["scratch"], { enableQuotas: false });

            expect(sourceUsageRequests).toBe(0);
        });

        it("isn't loaded for an anonymous user", async () => {
            useUserStore().currentUser = {
                isAnonymous: true,
                total_disk_usage: 0,
                nice_total_disk_usage: "0 bytes",
                quota_percent: 0,
            };

            await startWatchingWithQuotaSources(["scratch"]);

            expect(sourceUsageRequests).toBe(0);
        });

        it("is loaded once a user arrives after the watching started", async () => {
            await startWatchingWithQuotaSources(["scratch"]);
            expect(sourceUsageRequests).toBe(0);

            useUserStore().currentUser = getFakeRegisteredUser();
            await flushPromises();

            expect(sourceUsageRequests).toBe(1);
        });
    });
});
