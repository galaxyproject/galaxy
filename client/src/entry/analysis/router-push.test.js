import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import { eventBus } from "@/utils/eventBus";

import { patchRouterPush } from "./router-push";

// mock Galaxy object
const { mockGalaxy } = vi.hoisted(() => ({
    mockGalaxy: {
        frame: {
            active: false,
            add: vi.fn(),
        },
    },
}));

vi.mock("@/app", () => ({
    getGalaxyInstance: vi.fn(() => mockGalaxy),
}));

function createPatchedRouter() {
    const component = { template: "<div />" };
    const router = createRouter({
        history: createMemoryHistory("/galaxy"),
        routes: [
            { path: "/", component },
            { path: "/test/:name", component },
            { path: "/collection/new_list", component },
        ],
    });
    patchRouterPush(router);
    return router;
}

// router push handling tests
describe("router push changes", () => {
    beforeEach(() => {
        mockGalaxy.frame.active = false;
        mockGalaxy.frame.add.mockClear();
    });

    it("navigates when the window manager is inactive, even with a title", async () => {
        const router = createPatchedRouter();
        await router.push("/test/other");
        expect(router.currentRoute.value.fullPath).toBe("/test/other");
        await router.push("/test/something", { title: "test title" });
        expect(router.currentRoute.value.fullPath).toBe("/test/something");
        expect(mockGalaxy.frame.add).not.toHaveBeenCalled();
    });

    it("opens titled routes in the window manager when it is active", async () => {
        const router = createPatchedRouter();
        await router.push("/test/start");
        mockGalaxy.frame.active = true;
        const result = router.push("/test/tryagain", { title: "test title" });
        expect(result).toBeUndefined();
        expect(mockGalaxy.frame.add).toHaveBeenCalledWith({ title: "test title", url: "/test/tryagain" });
        expect(router.currentRoute.value.fullPath).toBe("/test/start");
    });

    it("navigates when the window manager is active but the route has no title or opts out", async () => {
        const router = createPatchedRouter();
        mockGalaxy.frame.active = true;
        await router.push("/test/untitled");
        expect(router.currentRoute.value.fullPath).toBe("/test/untitled");
        await router.push("/test/optout", { title: "test title", preventWindowManager: true });
        expect(router.currentRoute.value.fullPath).toBe("/test/optout");
        expect(mockGalaxy.frame.add).not.toHaveBeenCalled();
    });

    it("emits router-push for every navigation, including duplicates", async () => {
        const router = createPatchedRouter();
        const listener = vi.fn();
        eventBus.on("router-push", listener);
        await router.push("/test/same");
        await router.push("/test/same");
        eventBus.off("router-push", listener);
        expect(listener).toHaveBeenCalledTimes(2);
    });

    it("adds a key to forced string routes", async () => {
        const router = createPatchedRouter();
        await router.push("/test/forceroute", { force: true });
        expect(router.currentRoute.value.path).toBe("/test/forceroute");
        expect(router.currentRoute.value.query.__vkey__).toBeDefined();
    });

    it("does not double the router base for forced object routes", async () => {
        const router = createPatchedRouter();
        await router.push({ path: "/collection/new_list", query: { advanced: "false" } }, { force: true });
        const { fullPath, query } = router.currentRoute.value;
        expect(fullPath).not.toContain("/galaxy");
        expect(fullPath).toContain("__vkey__");
        expect(query.advanced).toBe("false");
    });

    it("keeps a query embedded in a forced object route's path", async () => {
        const router = createPatchedRouter();
        await router.push({ path: "/collection/new_list?advanced=true" }, { force: true });
        const { path, query } = router.currentRoute.value;
        expect(path).toBe("/collection/new_list");
        expect(query.advanced).toBe("true");
        expect(query.__vkey__).toBeDefined();
    });
});
