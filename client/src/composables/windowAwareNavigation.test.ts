import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import { getGalaxyInstance } from "@/app";
import { Toast } from "@/composables/toast";

import { pushIgnoringNavCancel } from "./windowAwareNavigation";

/**
 * A real `NavigationFailure` carries a non-exported internal symbol that
 * `isNavigationFailure()` checks for, so a hand-built error can't satisfy it.
 * Drive an actual router into a guard-cancelled navigation to get a genuine one.
 */
async function createCancelledNavigationError() {
    const router = createRouter({
        history: createMemoryHistory(),
        routes: [
            { path: "/", component: { template: "<div />" } },
            { path: "/pages/list", component: { template: "<div />" } },
        ],
    });
    await router.push("/");
    router.beforeEach(() => false);
    return router.push("/pages/list");
}

vi.mock("@/app");
vi.mock("@/composables/toast");

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
        // vue-router 4 resolves push() with the NavigationFailure rather than rejecting,
        // but the monkeypatch this stands in for re-rejects with it (see router-push.js),
        // so that's what pushIgnoringNavCancel's `.catch()` actually sees.
        const aborted = await createCancelledNavigationError();
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
