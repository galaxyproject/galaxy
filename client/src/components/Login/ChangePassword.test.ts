import { composeStories } from "@storybook/vue3-vite";
import { createTestRouter, nth } from "@tests/vitest/helpers";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import type { VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import * as ChangePasswordStories from "./ChangePassword.stories";

const stories = composeStories(ChangePasswordStories);
const mountStory = useStoryMount();
const { server, http } = useServerMock();

const resetLink = stories.ResetFromEmailLink.args;
const passwordExpired = stories.PasswordExpired.args;

/** Records the bodies posted to the legacy password change endpoint; the story still answers. */
function capturePasswordChanges() {
    const bodies: Record<string, unknown>[] = [];
    server.use(
        http.untyped.post("/user/change_password", async ({ request }) => {
            bodies.push((await request.clone().json()) as Record<string, unknown>);
        }),
    );
    return bodies;
}

async function mountChangePassword(story: StoryOf<typeof stories>) {
    const router = createTestRouter();
    // Start away from home, so the redirect after a successful change is observable.
    await router.push("/change-password");
    const wrapper = mountStory(story, { router });
    return { wrapper, router, changes: capturePasswordChanges() };
}

async function submit(wrapper: VueWrapper) {
    await wrapper.find("button[type='submit']").trigger("submit");
    await flushPromises();
}

describe("ChangePassword", () => {
    it("associates each password field with its visible label", async () => {
        const { wrapper } = await mountChangePassword(stories.PasswordExpired);
        const labels = wrapper.findAll("label");
        expect(labels.map((label) => label.text())).toEqual(["Current Password", "New Password", "Confirm password"]);
        const ids = labels.map((label) => label.attributes("for"));
        expect(new Set(ids).size).toBe(3);
        for (const id of ids) {
            expect(wrapper.find(`input[id="${id}"]`).attributes("type")).toBe("password");
        }
    });

    it("shows the message it was given as a warning", async () => {
        const { wrapper } = await mountChangePassword(stories.PasswordExpired);

        expect(wrapper.find(".alert-warning").exists()).toBe(true);
    });

    it("posts the reset token, the new password and its confirmation, then goes home", async () => {
        const { wrapper, router, changes } = await mountChangePassword(stories.ResetFromEmailLink);

        const inputs = wrapper.findAll("input");
        expect(inputs.length).toBe(2);
        await nth(inputs, 0).setValue("test_first_pwd");
        await nth(inputs, 1).setValue("test_second_pwd");
        await submit(wrapper);

        expect(changes).toHaveLength(1);
        expect(changes[0]).toMatchObject({
            token: resetLink.token,
            password: "test_first_pwd",
            confirm: "test_second_pwd",
        });
        expect(changes[0]).not.toHaveProperty("id");
        expect(router.currentRoute.value.path).toBe("/");
    });

    it("posts the expired user's id and their current password, keeping the message", async () => {
        const { wrapper, router, changes } = await mountChangePassword(stories.PasswordExpired);

        await wrapper.find("input").setValue("current_password");
        await submit(wrapper);

        expect(changes).toHaveLength(1);
        expect(changes[0]).toMatchObject({ id: passwordExpired.expiredUser, current: "current_password" });
        expect(changes[0]).not.toHaveProperty("token");
        expect(wrapper.find(".alert").text()).toBe(passwordExpired.messageText);
        expect(router.currentRoute.value.path).toBe("/");
    });

    it("shows Galaxy's refusal as a danger alert and stays on the form", async () => {
        const { wrapper, router, changes } = await mountChangePassword(stories.ResetLinkExpired);

        await submit(wrapper);

        expect(changes).toHaveLength(1);
        expect(wrapper.find(".alert-danger").exists()).toBe(true);
        expect(router.currentRoute.value.path).toBe("/change-password");
    });
});
