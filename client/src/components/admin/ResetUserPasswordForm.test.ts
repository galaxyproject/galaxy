import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type Vue from "vue";

import { useServerMock } from "@/api/client/__mocks__";

import ResetUserPasswordForm from "./ResetUserPasswordForm.vue";

const { server, http } = useServerMock();
const localVue = getLocalVue();
const mockPush = vi.fn();

vi.mock("vue-router/composables", () => ({
    useRouter: () => ({
        push: (...args: unknown[]) => mockPush(...args),
    }),
}));

function detailedUser(id: string, email: string) {
    return {
        id,
        email,
        username: email.split("@")[0]!,
        deleted: false,
        purged: false,
        is_admin: false,
        preferences: {},
        quota: "unlimited",
        total_disk_usage: 0,
        nice_total_disk_usage: "0 bytes",
    };
}

async function mountTarget() {
    server.use(
        http.get("/api/users/{user_id}", ({ response }) => response(200).json(detailedUser("u1", "user1@example.org"))),
    );
    const wrapper = mount(ResetUserPasswordForm as object, {
        localVue,
        propsData: { userId: "u1" },
        stubs: { FontAwesomeIcon: true },
    });
    await flushPromises();
    return wrapper;
}

function captureReset() {
    const requests: unknown[] = [];
    server.use(
        http.put("/api/users/{user_id}/password", async ({ request, response }) => {
            requests.push(await request.json());
            return response(204).empty();
        }),
    );
    return requests;
}

async function submit(wrapper: Wrapper<Vue>, password: string, confirm: string) {
    await wrapper.find("#admin-reset-password").setValue(password);
    await wrapper.find("#admin-reset-password-confirm").setValue(confirm);
    await wrapper.find("#admin-reset-password-submit").trigger("click");
    await flushPromises();
}

describe("ResetUserPasswordForm.vue", () => {
    beforeEach(() => {
        mockPush.mockClear();
    });

    it("shows the user's email", async () => {
        const wrapper = await mountTarget();
        expect(wrapper.text()).toContain("Reset password for 'user1@example.org'");
    });

    it("does not submit an empty password", async () => {
        const requests = captureReset();
        const wrapper = await mountTarget();
        await submit(wrapper, "", "");
        expect(wrapper.text()).toContain("Please enter a new password.");
        expect(requests).toEqual([]);
    });

    it("does not submit when the passwords do not match", async () => {
        const requests = captureReset();
        const wrapper = await mountTarget();
        await submit(wrapper, "newpassword1", "otherpassword1");
        expect(wrapper.text()).toContain("Passwords do not match.");
        expect(requests).toEqual([]);
        expect(mockPush).not.toHaveBeenCalled();
    });

    it("sets the new password", async () => {
        const requests = captureReset();
        const wrapper = await mountTarget();
        await submit(wrapper, "newpassword1", "newpassword1");
        expect(requests).toEqual([{ password: "newpassword1" }]);
        expect(mockPush).toHaveBeenCalledWith(
            `/admin/users?message=${encodeURIComponent("Password reset for user1@example.org.")}`,
        );
    });

    it("shows the API error", async () => {
        server.use(
            http.put("/api/users/{user_id}/password", ({ response }) =>
                response("4XX").json(
                    { err_msg: "Use a password of at least 6 characters.", err_code: 400 },
                    { status: 400 },
                ),
            ),
        );
        const wrapper = await mountTarget();
        await submit(wrapper, "short", "short");
        expect(wrapper.text()).toContain("Use a password of at least 6 characters.");
        expect(mockPush).not.toHaveBeenCalled();
    });

    it("cannot be saved when the user fails to load", async () => {
        server.use(
            http.get("/api/users/{user_id}", ({ response }) =>
                response("4XX").json({ err_msg: "User not found.", err_code: 404 }, { status: 404 }),
            ),
        );
        const wrapper = mount(ResetUserPasswordForm as object, {
            localVue,
            propsData: { userId: "u1" },
            stubs: { FontAwesomeIcon: true },
        });
        await flushPromises();
        expect(wrapper.text()).toContain("User not found.");
        expect(wrapper.find("#admin-reset-password-submit").exists()).toBe(false);
    });
});
