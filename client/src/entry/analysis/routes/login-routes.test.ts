import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import { getGalaxyInstance } from "@/app";

import LoginRoutes from "./login-routes";

vi.mock("@/app");

const LANDING_PATH = "/tool_landings/1234-5678?public=true";

function setUser(id: string | null) {
    vi.mocked(getGalaxyInstance).mockReturnValue({ user: { id } } as ReturnType<typeof getGalaxyInstance>);
}

/** Drive the real router, so this covers the route wiring and not just the guard. */
async function navigateTo(path: string) {
    const router = createRouter({ history: createMemoryHistory(), routes: LoginRoutes });
    await router.push(path);
    return router;
}

describe("login entry routes", () => {
    beforeEach(() => {
        vi.resetAllMocks();
    });

    it.each([
        { entry: "login", path: "/login/start" },
        { entry: "registration", path: "/register/start" },
    ])("renders the $entry page for anonymous users", async ({ path }) => {
        setUser(null);

        const router = await navigateTo(path);

        expect(router.currentRoute.value.path).toEqual(path);
        // A route-level redirect returning undefined used to leave no matched component.
        expect(router.currentRoute.value.matched).toHaveLength(1);
        expect(router.currentRoute.value.matched[0]?.components?.default).toBeTruthy();
    });

    it("keeps the pending destination on the route for the login form to use", async () => {
        setUser(null);
        const router = await navigateTo(`/login/start?redirect=${encodeURIComponent(LANDING_PATH)}`);
        expect(router.currentRoute.value.path).toEqual("/login/start");
        expect(router.currentRoute.value.query.redirect).toEqual(LANDING_PATH);
    });

    it.each([
        { entry: "login", path: "/login/start" },
        { entry: "registration", path: "/register/start" },
    ])("sends a logged-in user from $entry to the pending destination", async ({ path }) => {
        setUser("f2db41e1fa331b3e");

        const router = await navigateTo(`${path}?redirect=${encodeURIComponent(LANDING_PATH)}`);

        expect(router.currentRoute.value.fullPath).toEqual(LANDING_PATH);
    });

    it("sends a logged-in user home when nothing is pending", async () => {
        setUser("f2db41e1fa331b3e");
        const router = await navigateTo("/login/start");
        expect(router.currentRoute.value.path).toEqual("/");
    });

    it("refuses to bounce a logged-in user off this Galaxy", async () => {
        setUser("f2db41e1fa331b3e");
        const router = await navigateTo("/login/start?redirect=https%3A%2F%2Fevil.example.com%2F");
        expect(router.currentRoute.value.path).toEqual("/");
    });

    it("renders the password reset page and preserves the email for anonymous users", async () => {
        setUser(null);
        const router = await navigateTo("/login/reset_password?email=test%40example.com");

        expect(router.currentRoute.value.path).toEqual("/login/reset_password");
        expect(router.currentRoute.value.query.email).toEqual("test@example.com");
        expect(router.currentRoute.value.matched).toHaveLength(1);
    });
});
