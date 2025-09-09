import "tests/jest/mockHelpPopovers";

import { getFakeRegisteredUser } from "@tests/test-data";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import { useServerMock } from "@/api/client/__mocks__";
import { useUserStore } from "@/stores/userStore";
import { userLogoutClient } from "@/utils/logout";

import UserDeletion from "./UserDeletion.vue";

jest.mock("@/utils/logout", () => ({
    userLogoutClient: jest.fn(),
}));

const userLogoutClientMock = jest.mocked(userLogoutClient);

const localVue = getLocalVue(true);
const { server, http } = useServerMock();

const TEST_USER_ID = "myTestUserId";
const TEST_EMAIL = `${TEST_USER_ID}@test.com`;

async function mountComponent() {
    const pinia = createPinia();

    const wrapper = mount(UserDeletion as object, {
        localVue,
        pinia,
    });

    const userStore = useUserStore();
    userStore.currentUser = getFakeRegisteredUser({ email: TEST_EMAIL, id: TEST_USER_ID });

    await flushPromises();

    return wrapper;
}

describe("UserDeletion.vue", () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    it("renders the deletion modal with warning", async () => {
        const wrapper = await mountComponent();

        expect(wrapper.find("#modal-user-deletion").exists()).toBe(true);
        expect(wrapper.find(".alert-warning").exists()).toBe(true);
        expect(wrapper.text()).toContain("This action cannot be undone");
        expect(wrapper.text()).toContain("PERMANENTLY deleted");
    });

    it("shows input field for email confirmation and disables delete button initially", async () => {
        const wrapper = await mountComponent();

        const input = wrapper.find("#name-input");
        expect(input.exists()).toBe(true);

        const deleteButton = wrapper.find(".btn-danger");
        expect(deleteButton.attributes("disabled")).toBe("disabled");
    });

    it("enables delete button when email matches exactly", async () => {
        const wrapper = await mountComponent();

        const input = wrapper.find("#name-input");
        await input.setValue(TEST_EMAIL);

        const deleteButton = wrapper.find(".btn-danger");
        expect(deleteButton.attributes("disabled")).toBeUndefined();
    });

    it("shows validation state after input blur", async () => {
        const wrapper = await mountComponent();

        const input = wrapper.find("#name-input");
        await input.setValue("wrong@email.com");

        expect(wrapper.text()).toContain("Email does not match the current user email");
    });

    it("successfully deletes user account and logs out", async () => {
        server.use(
            http.delete("/api/users/{user_id}", ({ response }) => {
                return response(200).json(getFakeRegisteredUser({ deleted: true }));
            }),
        );

        const wrapper = await mountComponent();

        const input = wrapper.find("#name-input");
        await input.setValue(TEST_EMAIL);

        const deleteButton = wrapper.find(".btn-danger");
        await deleteButton.trigger("click");

        await flushPromises();

        expect(userLogoutClientMock).toHaveBeenCalled();
    });
});
