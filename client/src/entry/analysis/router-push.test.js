import { describe, expect, it, vi } from "vitest";

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

vi.mock("@/app/index", () => ({
    getGalaxyInstance: vi.fn(() => mockGalaxy),
}));

// router push handling tests
describe("router push changes", () => {
    it("pushing routes", async () => {
        window.confirm = vi.fn();
        let currentLocation = null;
        const mockComplete = vi.fn();
        const mockContext = {
            confirmation: true,
            app: {
                $emit: vi.fn(),
            },
        };
        const mockRouter = {
            prototype: {
                push: (location) => {
                    currentLocation = location;
                    return { catch: mockComplete };
                },
            },
        };
        patchRouterPush(mockRouter);
        const push = mockRouter.prototype.push;
        // route will be rejected while confirmation is required
        push.call(mockContext, "/test/name");
        expect(currentLocation).toBe(null);
        expect(mockComplete.mock.results.length).toBe(0);
        expect(window.confirm.mock.calls[0][0]).toBe("There are unsaved changes which will be lost.");
        // route should properly parse to original push
        mockContext.confirmation = false;
        push.call(mockContext, "/test/other");
        expect(currentLocation).toBe("/test/other");
        expect(mockComplete.mock.results.length).toBe(1);
        // route should properly parse to original push despite title
        const title = "test title";
        push.call(mockContext, "/test/something", { title });
        expect(currentLocation).toBe("/test/something");
        expect(mockComplete.mock.results.length).toBe(2);
        // route should be handled by calling the window manager
        mockGalaxy.frame.active = true;
        push.call(mockContext, "/test/tryagain", { title });
        expect(currentLocation).toBe("/test/something");
        push.call(mockContext, "/test/openanotherone", { title });
        expect(mockComplete.mock.results.length).toBe(2);
        expect(mockGalaxy.frame.add.mock.results.length).toBe(2);
        // route should be handled by router again
        mockGalaxy.frame.active = false;
        push.call(mockContext, "/test/regularagain", { title });
        expect(currentLocation).toBe("/test/regularagain");
        push.call(mockContext, "/test/openanotherone", { title });
        expect(mockComplete.mock.results.length).toBe(4);
        expect(mockGalaxy.frame.add.mock.results.length).toBe(2);
        // force route should modify location by adding key
        mockGalaxy.frame.active = false;
        push.call(mockContext, "/test/forceroute", { force: true });
        expect(currentLocation).toMatch(new RegExp(`/test/forceroute?.*vkey.*`));
    });

    it("does not double the router base for forced object routes", () => {
        const base = "/galaxy";
        let pushed = null;
        const mockContext = {
            confirmation: false,
            app: { $emit: vi.fn() },
            resolve(location) {
                const rel = typeof location === "object" ? location.path : location;
                return { href: `${base}${rel}`, route: { fullPath: rel } };
            },
        };
        const mockRouter = {
            prototype: {
                push: (location) => {
                    pushed = location;
                    return { catch: vi.fn() };
                },
            },
        };
        patchRouterPush(mockRouter);

        mockRouter.prototype.push.call(mockContext, { path: "/collection/new_list?advanced=false" }, { force: true });

        expect(pushed.fullPath).not.toContain(base);
        expect(pushed.fullPath).toContain("__vkey__");
    });
});
