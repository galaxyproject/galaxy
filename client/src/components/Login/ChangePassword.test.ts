import { createTestRouter, getLocalVue, nth, withPlugins } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import ChangePassword from "./ChangePassword.vue";

const { server, http } = useServerMock();

/** Records the bodies posted to the legacy password change endpoint. */
function capturePasswordChanges() {
    const bodies: Record<string, unknown>[] = [];
    server.use(
        http.untyped.post("/user/change_password", async ({ request }) => {
            bodies.push((await request.json()) as Record<string, unknown>);
            return HttpResponse.json({});
        }),
    );
    return bodies;
}

async function mountChangePassword(props: Record<string, string> = {}) {
    const router = createTestRouter();
    // Start away from home, so the redirect after a successful change is observable.
    await router.push("/change-password");
    const wrapper = mount(ChangePassword, {
        props: { messageText: "message_text", messageVariant: "message_variant", ...props },
        global: withPlugins(getLocalVue(), router),
    });
    return { wrapper, router };
}

async function submit(wrapper: VueWrapper) {
    await wrapper.find("button[type='submit']").trigger("submit");
    await flushPromises();
}

describe("ChangePassword", () => {
    it("renders the change password card with the message it was given", async () => {
        const { wrapper } = await mountChangePassword();

        expect(wrapper.find(".card-header").text()).toBe("Change your password");
        expect(wrapper.find(".alert").text()).toBe("message_text");
    });

    it("posts the new password and its confirmation, then goes home", async () => {
        const changes = capturePasswordChanges();
        const { wrapper, router } = await mountChangePassword();

        const inputs = wrapper.findAll("input");
        expect(inputs.length).toBe(2);
        expect(nth(inputs, 0).attributes("type")).toBe("password");
        expect(nth(inputs, 1).attributes("type")).toBe("password");
        await nth(inputs, 0).setValue("test_first_pwd");
        await nth(inputs, 1).setValue("test_second_pwd");
        await submit(wrapper);

        expect(changes).toHaveLength(1);
        expect(changes[0]).toMatchObject({ password: "test_first_pwd", confirm: "test_second_pwd" });
        expect(router.currentRoute.value.path).toBe("/");
    });

    it("posts the reset token, the expired user's id and their current password", async () => {
        const changes = capturePasswordChanges();
        const { wrapper, router } = await mountChangePassword({ token: "test_token", expiredUser: "expired_user" });

        const currentPassword = wrapper.find("input");
        expect(currentPassword.attributes("type")).toBe("password");
        await currentPassword.setValue("current_password");
        await submit(wrapper);

        expect(changes).toHaveLength(1);
        expect(changes[0]).toMatchObject({ token: "test_token", id: "expired_user", current: "current_password" });
        expect(wrapper.find(".alert").text()).toBe("message_text");
        expect(router.currentRoute.value.path).toBe("/");
    });
});
