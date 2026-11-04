import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { useQuotaUsageStore } from "@/stores/quotaUsageStore";

const { server, http } = useServerMock();

describe("quotaUsageStore", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
    });

    it("reloads again when asked to while an older request is still in flight", async () => {
        let requests = 0;
        server.use(
            http.get("/api/users/{user_id}/usage", ({ response }) => {
                requests++;
                return response(200).json([{ quota_source_label: null, total_disk_usage: requests * 1024 }]);
            }),
        );
        const store = useQuotaUsageStore();

        void store.loadQuotaUsages();
        await store.loadQuotaUsages(true);
        await flushPromises();

        expect(requests).toBe(2);
        expect(store.quotaUsages?.map((usage) => usage.totalDiskUsageInBytes)).toEqual([2048]);
    });

    it("stops reporting a source over quota once reloading it alone shows it under quota", async () => {
        const overQuota = { quota_source_label: "secure", quota_bytes: 1000, total_disk_usage: 1001 };
        server.use(
            http.get("/api/users/{user_id}/usage", ({ response }) => response(200).json([overQuota])),
            http.get("/api/users/{user_id}/usage/{label}", ({ response }) =>
                response(200).json({ ...overQuota, total_disk_usage: 400 }),
            ),
        );
        const store = useQuotaUsageStore();
        await store.loadQuotaUsages();
        expect(store.otherSourcesOverQuota.map((usage) => usage.rawSourceLabel)).toEqual(["secure"]);

        await store.loadQuotaUsageForSource("secure", true);

        expect(store.otherSourcesOverQuota).toEqual([]);
    });
});
