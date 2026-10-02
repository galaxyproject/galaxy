import axios from "axios";
import flushPromises from "flush-promises";
import { afterEach, describe, expect, it, vi } from "vitest";

import { getGalaxyInstance } from "@/app";
import { Toast } from "@/composables/toast";

import { userLogout } from "./logout";

vi.mock("axios", () => ({
    default: {
        get: vi.fn(),
    },
}));

vi.mock("@/app", () => ({
    getGalaxyInstance: vi.fn(() => ({
        config: { post_user_logout_href: "/", enable_oidc: false },
        session_csrf_token: "stale",
    })),
}));

vi.mock("@/utils/redirect", () => ({
    withPrefix: (path) => `${window.location.origin}${path}`,
}));

vi.mock("@/composables/toast", () => ({
    Toast: { error: vi.fn() },
}));

describe("userLogout", () => {
    afterEach(() => {
        vi.clearAllMocks();
        vi.restoreAllMocks();
    });

    it("reports a rejected logout request", async () => {
        axios.get.mockRejectedValue({
            response: { status: 400, data: { err_msg: "Invalid session token." } },
        });
        userLogout(true);
        await flushPromises();
        expect(axios.get).toHaveBeenCalledWith(expect.stringContaining("logout_all=true"));
        expect(Toast.error).toHaveBeenCalledWith("Invalid session token.", "Logout failed");
    });

    it("finishes logging out when only the identity provider logout fails", async () => {
        vi.mocked(getGalaxyInstance).mockReturnValue({
            config: { post_user_logout_href: "/logged_out", enable_oidc: true },
            session_csrf_token: "token",
        });
        const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
        axios.get.mockResolvedValueOnce({ data: {} }).mockRejectedValueOnce(new Error("Network Error"));
        userLogout();
        await flushPromises();
        expect(axios.get).toHaveBeenLastCalledWith(expect.stringContaining("/authnz/logout"));
        expect(warn).toHaveBeenCalled();
        expect(Toast.error).not.toHaveBeenCalled();
        expect(window.top.location.href).toContain("/logged_out");
    });
});
