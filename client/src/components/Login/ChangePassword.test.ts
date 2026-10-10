import { composeStories } from "@storybook/vue3-vite";
import { nth } from "@tests/vitest/helpers";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import type { VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, describe, expect, it, vi } from "vitest";

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

/** Stubs the full-page reload that picks up the session after a successful change. */
function stubPageReload() {
    return vi.spyOn(window.location, "replace").mockImplementation(() => {});
}

function mountChangePassword(story: StoryOf<typeof stories>) {
    const reload = stubPageReload();
    const wrapper = mountStory(story);
    return { wrapper, reload, changes: capturePasswordChanges() };
}

async function submit(wrapper: VueWrapper) {
    await wrapper.find("button[type='submit']").trigger("submit");
    await flushPromises();
}

describe("ChangePassword", () => {
    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("associates each password field with its visible label", async () => {
        const { wrapper } = mountChangePassword(stories.PasswordExpired);
        const labels = wrapper.findAll("label");
        expect(labels.map((label) => label.text())).toEqual(["Current Password", "New Password", "Confirm password"]);
        const ids = labels.map((label) => label.attributes("for"));
        expect(new Set(ids).size).toBe(3);
        for (const id of ids) {
            expect(wrapper.find(`input[id="${id}"]`).attributes("type")).toBe("password");
        }
    });

    it("shows the message it was given as a warning", async () => {
        const { wrapper } = mountChangePassword(stories.PasswordExpired);

        expect(wrapper.find(".alert-warning").exists()).toBe(true);
    });

    it("posts the reset token, the new password and its confirmation, then reloads home", async () => {
        const { wrapper, reload, changes } = mountChangePassword(stories.ResetFromEmailLink);

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
        expect(reload).toHaveBeenCalledExactlyOnceWith("/");
    });

    it("posts the expired user's id and their current password, keeping the message", async () => {
        const { wrapper, reload, changes } = mountChangePassword(stories.PasswordExpired);

        await wrapper.find("input").setValue("current_password");
        await submit(wrapper);

        expect(changes).toHaveLength(1);
        expect(changes[0]).toMatchObject({ id: passwordExpired.expiredUser, current: "current_password" });
        expect(changes[0]).not.toHaveProperty("token");
        expect(wrapper.find(".alert").text()).toBe(passwordExpired.messageText);
        expect(reload).toHaveBeenCalledExactlyOnceWith("/");
    });

    it("shows Galaxy's refusal as a danger alert and stays on the form", async () => {
        const { wrapper, reload, changes } = mountChangePassword(stories.ResetLinkExpired);

        await submit(wrapper);

        expect(changes).toHaveLength(1);
        expect(wrapper.find(".alert-danger").exists()).toBe(true);
        expect(reload).not.toHaveBeenCalled();
    });
});
