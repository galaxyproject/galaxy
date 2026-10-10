import { composeStories } from "@storybook/vue3-vite";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import type { VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { clickModalButton } from "@/components/BaseComponents/test-utils";
import { userLogoutClient } from "@/utils/logout";

import * as UserDeletionStories from "./UserDeletion.stories";

vi.mock("@/utils/logout", () => ({
    userLogoutClient: vi.fn(),
}));

const stories = composeStories(UserDeletionStories);
const mountStory = useStoryMount();
const { server, http } = useServerMock();

// The signed-in user in the stories.
const TEST_USER_ID = "f2db41e1fa331b3e";
const TEST_EMAIL = "alice@example.org";
const DELETE_BUTTON_TEXT = "Delete Account Permanently";

const SELECTORS = {
    DELETE_BUTTON: "button.g-red",
    EMAIL_INPUT: "#name-input",
    ERROR_ALERT: ".alert-danger",
    MODAL: "#modal-user-deletion",
    WARNING: ".alert-warning",
};

async function mountUserDeletion(story: StoryOf<typeof stories> = stories.AwaitingConfirmation) {
    const wrapper = mountStory(story);
    await flushPromises();
    return wrapper;
}

async function enterEmail(wrapper: VueWrapper, email: string) {
    await wrapper.find(SELECTORS.EMAIL_INPUT).setValue(email);
}

/** Records the ids of users the dialog asks Galaxy to delete; the story still answers. */
function recordDeletedUserIds() {
    const deletedUserIds: string[] = [];
    server.use(
        http.delete("/api/users/{user_id}", ({ params }) => {
            deletedUserIds.push(params.user_id);
        }),
    );
    return deletedUserIds;
}

describe("UserDeletion.vue", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("renders the deletion modal with warning", async () => {
        const wrapper = await mountUserDeletion();

        expect(wrapper.find(SELECTORS.MODAL).exists()).toBe(true);
        expect(wrapper.find(SELECTORS.WARNING).exists()).toBe(true);
        expect(wrapper.text()).toContain("This action cannot be undone");
        expect(wrapper.text()).toContain("PERMANENTLY deleted");
    });

    it("shows input field for email confirmation and disables delete button initially", async () => {
        const wrapper = await mountUserDeletion();

        expect(wrapper.find(SELECTORS.EMAIL_INPUT).exists()).toBe(true);
        expect(wrapper.find(SELECTORS.DELETE_BUTTON).attributes("aria-disabled")).toBe("true");
    });

    it("enables delete button when email matches exactly", async () => {
        const wrapper = await mountUserDeletion();

        await enterEmail(wrapper, TEST_EMAIL);

        expect(wrapper.find(SELECTORS.DELETE_BUTTON).attributes("aria-disabled")).toBeUndefined();
    });

    it("shows validation state after input blur", async () => {
        const wrapper = await mountUserDeletion();

        await enterEmail(wrapper, "wrong@email.com");
        await wrapper.find(SELECTORS.EMAIL_INPUT).trigger("blur");

        expect(wrapper.text()).toContain("Email does not match the current user email");
    });

    it("deletes the current user's account and logs out when deletion is confirmed", async () => {
        const wrapper = await mountUserDeletion();
        const deletedUserIds = recordDeletedUserIds();
        await enterEmail(wrapper, TEST_EMAIL);

        await clickModalButton(wrapper, DELETE_BUTTON_TEXT);

        expect(deletedUserIds).toEqual([TEST_USER_ID]);
        expect(userLogoutClient).toHaveBeenCalledOnce();
    });

    it("shows an error in the dialog and stays logged in when Galaxy refuses the deletion", async () => {
        const wrapper = await mountUserDeletion(stories.SelfDeletionNotAllowed);
        const deletedUserIds = recordDeletedUserIds();
        await enterEmail(wrapper, TEST_EMAIL);

        await clickModalButton(wrapper, DELETE_BUTTON_TEXT);

        expect(deletedUserIds).toEqual([TEST_USER_ID]);
        expect(wrapper.find(`${SELECTORS.MODAL} ${SELECTORS.ERROR_ALERT}`).text()).not.toBe("");
        expect(wrapper.find(SELECTORS.EMAIL_INPUT).exists()).toBe(true);
        expect(userLogoutClient).not.toHaveBeenCalled();
    });
});
