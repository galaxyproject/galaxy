import { beforeEach, describe, expect, it, vi } from "vitest";

import { getGalaxyInstance } from "@/app";
import { Toast } from "@/composables/toast";

import { pushIgnoringNavCancel } from "./windowAwareNavigation";

vi.mock("@/app");
vi.mock("@/composables/toast", () => ({
    Toast: { error: vi.fn() },
}));

const mockGetGalaxyInstance = vi.mocked(getGalaxyInstance);
const mockToastError = vi.mocked(Toast.error);

/** Stands in for the monkeypatched router (entry/analysis/router-push.js). */
function fakeRouter(push: (...args: unknown[]) => unknown) {
    return { push: vi.fn(push) } as never;
}

describe("pushIgnoringNavCancel", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockGetGalaxyInstance.mockReturnValue({ frame: { active: false } } as never);
    });

    it("tolerates a push that returns nothing", () => {
        // The monkeypatch returns undefined -- no promise to attach to -- when the window
        // manager takes the navigation, or when a confirmation is declined.
        const router = fakeRouter(() => undefined);

        expect(() => pushIgnoringNavCancel(router, "/pages/list")).not.toThrow();
    });

    it("swallows a cancelled navigation", async () => {
        const aborted = Object.assign(new Error("Navigation aborted"), { _isRouter: true, type: 4 });
        const router = fakeRouter(() => Promise.reject(aborted));

        pushIgnoringNavCancel(router, "/pages/list");
        await new Promise(process.nextTick);

        expect(mockToastError).not.toHaveBeenCalled();
    });

    it("reports a navigation that failed for any other reason", async () => {
        const router = fakeRouter(() => Promise.reject(new Error("boom")));

        pushIgnoringNavCancel(router, "/pages/list");
        await new Promise(process.nextTick);

        expect(mockToastError).toHaveBeenCalledWith("boom", "Navigation failed");
    });
});
