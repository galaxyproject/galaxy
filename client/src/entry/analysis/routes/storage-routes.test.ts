import { describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import storageRoutes from "./storage-routes";

vi.mock("@/components/User/DiskUsage/Management/StorageManager.vue", () => ({ default: {} }));
vi.mock("@/components/User/DiskUsage/StorageDashboard.vue", () => ({ default: {} }));
vi.mock("@/components/User/DiskUsage/Visualizations/HistoriesStorageOverview.vue", () => ({ default: {} }));
vi.mock("@/components/User/DiskUsage/Visualizations/HistoryStorageOverview.vue", () => ({ default: {} }));
vi.mock("@/components/User/DiskUsage/Visualizations/ObjectStoresStorageOverview.vue", () => ({ default: {} }));
vi.mock("@/components/User/DiskUsage/Visualizations/ObjectStoreStorageOverview.vue", () => ({ default: {} }));
vi.mock("@/entry/analysis/modules/Base.vue", () => ({ default: {} }));

describe("storage routes", () => {
    it("sends unknown storage paths, like the preferences page's /storage/dashboard link, to the dashboard", async () => {
        const router = createRouter({ history: createMemoryHistory(), routes: storageRoutes });

        await router.push("/storage/dashboard");

        expect(router.currentRoute.value.name).toBe("StorageDashboard");
    });
});
