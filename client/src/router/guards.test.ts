import { beforeEach, describe, expect, it, vi } from "vitest";
import type { NavigationGuardNext, Route } from "vue-router";

import { getGalaxyInstance } from "@/app";

import { redirectLoggedIn } from "./guards";

vi.mock("@/app");

const LANDING_PATH = "/tool_landings/1234-5678?public=true";

function runGuard(query: Route["query"] = {}) {
    const next = vi.fn();
    redirectLoggedIn({ query } as Route, {} as Route, next as unknown as NavigationGuardNext);
    return next;
}

function setUser(id: string | null) {
    vi.mocked(getGalaxyInstance).mockReturnValue({ user: { id } } as ReturnType<typeof getGalaxyInstance>);
}

describe("redirectLoggedIn", () => {
    beforeEach(() => {
        vi.resetAllMocks();
    });

    it("renders the login form for anonymous users", () => {
        setUser(null);
        expect(runGuard()).toHaveBeenCalledWith();
    });

    it("renders the login form when there is no Galaxy user at all", () => {
        vi.mocked(getGalaxyInstance).mockReturnValue({} as ReturnType<typeof getGalaxyInstance>);
        expect(runGuard()).toHaveBeenCalledWith();
    });

    it("sends logged-in users home when no destination is pending", () => {
        setUser("f2db41e1fa331b3e");
        expect(runGuard()).toHaveBeenCalledWith("/");
    });

    it("sends logged-in users to the pending destination, query string intact", () => {
        setUser("f2db41e1fa331b3e");
        expect(runGuard({ redirect: LANDING_PATH })).toHaveBeenCalledWith(LANDING_PATH);
    });

    it("refuses to bounce logged-in users off this Galaxy", () => {
        setUser("f2db41e1fa331b3e");
        expect(runGuard({ redirect: "https://evil.example.com/" })).toHaveBeenCalledWith("/");
        expect(runGuard({ redirect: "//evil.example.com/" })).toHaveBeenCalledWith("/");
    });

    it("does not bounce a logged-in user back to the login route", () => {
        setUser("f2db41e1fa331b3e");
        expect(runGuard({ redirect: "/login/start" })).toHaveBeenCalledWith("/");
    });
});
