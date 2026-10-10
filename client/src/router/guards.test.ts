import { beforeEach, describe, expect, it, vi } from "vitest";
import type { RouteLocationNormalized } from "vue-router";

import { getGalaxyInstance } from "@/app";

import { redirectLoggedIn } from "./guards";

vi.mock("@/app");

const LANDING_PATH = "/tool_landings/1234-5678?public=true";

function runGuard(query: RouteLocationNormalized["query"] = {}) {
    const route: RouteLocationNormalized = {
        path: "/login/start",
        fullPath: "/login/start",
        name: undefined,
        params: {},
        hash: "",
        query,
        matched: [],
        meta: {},
        redirectedFrom: undefined,
    };
    return redirectLoggedIn(route);
}

function setUser(id: string | null) {
    vi.mocked(getGalaxyInstance).mockReturnValue({ user: { id } } as ReturnType<typeof getGalaxyInstance>);
}

describe("redirectLoggedIn", () => {
    beforeEach(() => {
        vi.resetAllMocks();
    });

    it("allows anonymous users to enter the login route", () => {
        setUser(null);
        expect(runGuard()).toBeUndefined();
    });

    it("allows entry when there is no Galaxy user at all", () => {
        vi.mocked(getGalaxyInstance).mockReturnValue({} as ReturnType<typeof getGalaxyInstance>);
        expect(runGuard()).toBeUndefined();
    });

    it("sends logged-in users home when no destination is pending", () => {
        setUser("f2db41e1fa331b3e");
        expect(runGuard()).toBe("/");
    });

    it("sends logged-in users to the pending destination, query string intact", () => {
        setUser("f2db41e1fa331b3e");
        expect(runGuard({ redirect: LANDING_PATH })).toBe(LANDING_PATH);
    });

    it.each([
        { name: "absolute URL", redirect: "https://evil.example.com/" },
        { name: "protocol-relative URL", redirect: "//evil.example.com/" },
    ])("sends logged-in users home instead of a $name", ({ redirect }) => {
        setUser("f2db41e1fa331b3e");

        expect(runGuard({ redirect })).toBe("/");
    });

    it("sends logged-in users home instead of returning to the login route", () => {
        setUser("f2db41e1fa331b3e");

        expect(runGuard({ redirect: "/login/start" })).toBe("/");
    });
});
