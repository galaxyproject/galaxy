import { describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import LibraryRoutes from "./library-routes";

vi.mock("@/components/Libraries/LibrariesList.vue", () => ({ default: {} }));
vi.mock("@/components/Libraries/LibraryFolder/LibraryFolder.vue", () => ({ default: {} }));
vi.mock("@/components/Libraries/LibraryFolder/LibraryFolderDataset/LibraryDataset.vue", () => ({ default: {} }));
vi.mock("@/components/Libraries/LibraryFolder/LibraryFolderPermissions/LibraryFolderDatasetPermissions.vue", () => ({
    default: {},
}));
vi.mock("@/components/Libraries/LibraryFolder/LibraryFolderPermissions/LibraryFolderPermissions.vue", () => ({
    default: {},
}));
vi.mock("@/components/Libraries/LibraryPermissions/LibraryPermissions.vue", () => ({ default: {} }));
vi.mock("@/entry/analysis/modules/Base.vue", () => ({ default: {} }));

describe("library routes", () => {
    it("redirects a bare folder URL to its first page", async () => {
        const router = createRouter({ history: createMemoryHistory(), routes: LibraryRoutes });
        await router.push("/libraries/folders/F123");
        expect(router.currentRoute.value.path).toEqual("/libraries/folders/F123/page/1");
        expect(router.currentRoute.value.name).toEqual("LibraryFolder");
        expect(router.currentRoute.value.params.folder_id).toEqual("F123");
    });

    it("passes the folder page to LibraryFolder as a number", async () => {
        const router = createRouter({ history: createMemoryHistory(), routes: LibraryRoutes });
        await router.push("/libraries/folders/F123/page/3");
        const route = router.currentRoute.value;
        const propsFunction = route.matched.at(-1)?.props.default;
        expect(typeof propsFunction).toEqual("function");
        expect((propsFunction as (route: unknown) => unknown)(route)).toEqual({ folder_id: "F123", page: 3 });
    });
});
