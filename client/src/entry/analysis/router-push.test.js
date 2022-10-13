import { getGalaxyInstance } from "app/singleton";
import { patchRouterPush } from "./router-push";

// mock Galaxy object
jest.mock("app/singleton");
const mockGalaxy = {
    frame: {
        active: false,
        add: jest.fn(),
    },
};
getGalaxyInstance.mockImplementation(() => mockGalaxy);

// router push handling tests
describe("router push changes", () => {
    it("pushing routes", async () => {
        window.confirm = jest.fn();
        let currentLocation = null;
        const mockComplete = jest.fn();
        const mockContext = {
            confirmation: true,
            app: {
                $emit: jest.fn(),
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
        const results = mockComplete.mock.results;
        const windowResults = mockGalaxy.frame.add.mock.results;
        // route will be rejected while confirmation is required
        push.call(mockContext, "/test/name");
        expect(currentLocation).toBe(null);
        expect(results.length).toBe(0);
        expect(window.confirm.mock.calls[0][0]).toBe("There are unsaved changes which will be lost.");
        // route should properly parse to original push
        mockContext.confirmation = false;
        push.call(mockContext, "/test/other");
        expect(currentLocation).toBe("/test/other");
        expect(results.length).toBe(1);
        // route should properly parse to original push despite title
        const title = "test title";
        push.call(mockContext, "/test/something", { title });
        expect(currentLocation).toBe("/test/something");
        expect(results.length).toBe(2);
        // route should be handled by calling the window manager
        mockGalaxy.frame.active = true;
        push.call(mockContext, "/test/tryagain", { title });
        expect(currentLocation).toBe("/test/something");
        push.call(mockContext, "/test/openanotherone", { title });
        expect(results.length).toBe(2);
        expect(windowResults.length).toBe(2);
        // route should be handled by router again
        mockGalaxy.frame.active = false;
        push.call(mockContext, "/test/regularagain", { title });
        expect(currentLocation).toBe("/test/regularagain");
        push.call(mockContext, "/test/openanotherone", { title });
        expect(results.length).toBe(4);
        expect(windowResults.length).toBe(2);
        // force route should modify location by adding key
        mockGalaxy.frame.active = false;
        push.call(mockContext, "/test/forceroute", { force: true });
        expect(currentLocation).toMatch(new RegExp(`/test/forceroute?.*vkey.*`));
    });
});
