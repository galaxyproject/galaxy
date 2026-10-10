import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { clickModalButton } from "@/components/BaseComponents/test-utils";
import { useUserStore } from "@/stores/userStore";
import { userLogoutClient } from "@/utils/logout";

import UserDeletion from "./UserDeletion.vue";

vi.mock("@/utils/logout", () => ({
    userLogoutClient: vi.fn(),
}));

const localVue = getLocalVue();
const { server, http } = useServerMock();

enableAutoUnmount(afterEach);

const TEST_USER_ID = "myTestUserId";
const TEST_EMAIL = `${TEST_USER_ID}@test.com`;
const DELETE_BUTTON_TEXT = "Delete Account Permanently";

const SELECTORS = {
    DELETE_BUTTON: "button.g-red",
    EMAIL_INPUT: "#name-input",
    MODAL: "#modal-user-deletion",
    WARNING: ".alert-warning",
};

async function mountUserDeletion() {
    const pinia = createPinia();
    useUserStore(pinia).currentUser = getFakeRegisteredUser({ email: TEST_EMAIL, id: TEST_USER_ID });

    const wrapper = mount(UserDeletion, {
        global: withPlugins(localVue, pinia),
    });
    await flushPromises();

    return wrapper;
}

async function enterEmail(wrapper: VueWrapper, email: string) {
    await wrapper.find(SELECTORS.EMAIL_INPUT).setValue(email);
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
        const deletedUserIds: string[] = [];
        server.use(
            http.delete("/api/users/{user_id}", ({ params, response }) => {
                deletedUserIds.push(params.user_id);
                return response(200).json(getFakeRegisteredUser({ deleted: true }));
            }),
        );
        const wrapper = await mountUserDeletion();
        await enterEmail(wrapper, TEST_EMAIL);

        await clickModalButton(wrapper, DELETE_BUTTON_TEXT);

        expect(deletedUserIds).toEqual([TEST_USER_ID]);
        expect(userLogoutClient).toHaveBeenCalledOnce();
    });
});
