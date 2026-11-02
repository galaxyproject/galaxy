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
});
