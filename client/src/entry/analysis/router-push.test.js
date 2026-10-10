import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import { eventBus } from "@/utils/eventBus";

import { patchRouterPush } from "./router-push";

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

describe("patchRouterPush", () => {
    beforeEach(() => {
        mockGalaxy.frame.active = false;
        mockGalaxy.frame.add.mockClear();
    });

    it.each([
        { name: "untitled", path: "/test/other", options: {} },
        { name: "titled", path: "/test/something", options: { title: "test title" } },
    ])("navigates to a $name route when the window manager is inactive", async ({ path, options }) => {
        const router = createPatchedRouter();

        await router.push(path, options);

        expect(router.currentRoute.value.fullPath).toBe(path);
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

    it.each([
        { name: "has no title", path: "/test/untitled", options: {} },
        {
            name: "opts out of the window manager",
            path: "/test/optout",
            options: { title: "test title", preventWindowManager: true },
        },
    ])("navigates when the window manager is active but the route $name", async ({ path, options }) => {
        const router = createPatchedRouter();
        mockGalaxy.frame.active = true;

        await router.push(path, options);

        expect(router.currentRoute.value.fullPath).toBe(path);
        expect(mockGalaxy.frame.add).not.toHaveBeenCalled();
    });

    it("emits router-push for every navigation, including duplicates", async () => {
        const router = createPatchedRouter();
        const listener = vi.fn();
        eventBus.on("router-push", listener);
        try {
            await router.push("/test/same");
            await router.push("/test/same");

            expect(listener).toHaveBeenCalledTimes(2);
        } finally {
            eventBus.off("router-push", listener);
        }
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
        const { fullPath, path, query } = router.currentRoute.value;
        expect(path).toBe("/collection/new_list");
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
