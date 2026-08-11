import { beforeEach, describe, expect, it, vi } from "vitest";
import Vue from "vue";
import VueRouter from "vue-router";

import { getGalaxyInstance } from "@/app";

import LoginRoutes from "./login-routes";

vi.mock("@/app");

Vue.use(VueRouter);

const LANDING_PATH = "/tool_landings/1234-5678?public=true";

function setUser(id: string | null) {
    vi.mocked(getGalaxyInstance).mockReturnValue({ user: { id } } as ReturnType<typeof getGalaxyInstance>);
}

/** Drive the real router, so this covers the route wiring and not just the guard. */
async function navigateTo(path: string) {
    const router = new VueRouter({ mode: "abstract", routes: LoginRoutes });
    // vue-router rejects the push promise when a guard redirects; currentRoute still
    // settles on wherever the guard sent us, which is what we are asserting on.
    await router.push(path).catch(() => undefined);
    return router;
}

describe("login entry routes", () => {
    beforeEach(() => {
        vi.resetAllMocks();
    });

    it("renders the login page for anonymous users", async () => {
        setUser(null);
        const router = await navigateTo("/login/start");
        expect(router.currentRoute.path).toEqual("/login/start");
        // A route-level `redirect` function returning undefined would match nothing here,
        // leaving anonymous users with a blank page instead of the login form.
        expect(router.currentRoute.matched).toHaveLength(1);
        expect(router.currentRoute.matched[0]?.components?.default).toBeTruthy();
    });

    it("keeps the pending destination on the route for the login form to use", async () => {
        setUser(null);
        const router = await navigateTo(`/login/start?redirect=${encodeURIComponent(LANDING_PATH)}`);
        expect(router.currentRoute.path).toEqual("/login/start");
        expect(router.currentRoute.query.redirect).toEqual(LANDING_PATH);
    });

    it("sends a logged-in user straight to the pending destination", async () => {
        setUser("f2db41e1fa331b3e");
        const router = await navigateTo(`/login/start?redirect=${encodeURIComponent(LANDING_PATH)}`);
        expect(router.currentRoute.fullPath).toEqual(LANDING_PATH);
    });

    it("sends a logged-in user home when nothing is pending", async () => {
        setUser("f2db41e1fa331b3e");
        const router = await navigateTo("/login/start");
        expect(router.currentRoute.path).toEqual("/");
    });

    it("refuses to bounce a logged-in user off this Galaxy", async () => {
        setUser("f2db41e1fa331b3e");
        const router = await navigateTo("/login/start?redirect=https%3A%2F%2Fevil.example.com%2F");
        expect(router.currentRoute.path).toEqual("/");
    });

    it("applies the same treatment to the registration entry route", async () => {
        setUser("f2db41e1fa331b3e");
        const router = await navigateTo(`/register/start?redirect=${encodeURIComponent(LANDING_PATH)}`);
        expect(router.currentRoute.fullPath).toEqual(LANDING_PATH);
    });

    it("renders the registration page for anonymous users", async () => {
        // Only reachable this way when require_login is off -- with it on, the server
        // gate redirects first, because /register/start is not in its allowed paths.
        setUser(null);
        const router = await navigateTo("/register/start");
        expect(router.currentRoute.path).toEqual("/register/start");
        expect(router.currentRoute.matched).toHaveLength(1);
    });
});
