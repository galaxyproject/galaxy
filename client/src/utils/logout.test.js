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

    it("does not ask to end other sessions on a plain logout", async () => {
        axios.get.mockRejectedValue({ response: { status: 400, data: { err_msg: "Invalid session token." } } });
        userLogout();
        await flushPromises();
        expect(axios.get).toHaveBeenCalledOnce();
        expect(axios.get).toHaveBeenCalledWith(expect.not.stringContaining("logout_all"));
    });

    it("does not treat a non-boolean argument as logout all", async () => {
        vi.mocked(getGalaxyInstance).mockReturnValue({
            config: { post_user_logout_href: "/logged_out", enable_oidc: true },
            session_csrf_token: "token",
        });
        axios.get.mockResolvedValueOnce({ data: {} }).mockRejectedValueOnce({
            response: { status: 400, data: { err_msg: "Invalid session token." } },
        });
        userLogout(new MouseEvent("click"));
        await flushPromises();
        expect(axios.get).toHaveBeenCalledTimes(2);
        expect(axios.get).toHaveBeenNthCalledWith(1, expect.not.stringContaining("logout_all"));
        expect(axios.get).toHaveBeenNthCalledWith(2, expect.not.stringContaining("logout_all"));
    });

    it("reports a failed identity provider logout", async () => {
        vi.mocked(getGalaxyInstance).mockReturnValue({
            config: { post_user_logout_href: "/logged_out", enable_oidc: true },
            session_csrf_token: "token",
        });
        axios.get.mockRejectedValueOnce({
            response: { status: 500, data: { err_msg: "Identity provider unavailable." } },
        });
        userLogout();
        await flushPromises();
        expect(axios.get).toHaveBeenCalledOnce();
        expect(axios.get).toHaveBeenCalledWith(expect.stringContaining("/authnz/logout"));
        expect(Toast.error).toHaveBeenCalledWith("Identity provider unavailable.", "Logout failed");
    });

    it("falls back to the Galaxy logout when the identity provider logout has nothing to do", async () => {
        vi.mocked(getGalaxyInstance).mockReturnValue({
            config: { post_user_logout_href: "/logged_out", enable_oidc: true },
            session_csrf_token: "token",
        });
        axios.get.mockResolvedValueOnce({ data: {} }).mockRejectedValueOnce({
            response: { status: 400, data: { err_msg: "Invalid session token." } },
        });
        userLogout();
        await flushPromises();
        expect(axios.get).toHaveBeenLastCalledWith(expect.stringContaining("/user/logout"));
        expect(Toast.error).toHaveBeenCalledWith("Invalid session token.", "Logout failed");
    });
});
