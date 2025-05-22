import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import MountTarget from "./LoginIndex";

const mockPush = jest.fn();

jest.mock("vue-router/composables", () => ({
    useRouter: () => ({ push: mockPush }),
}));

const localVue = getLocalVue(true);

describe("LoginIndex", () => {
    let wrapper;

    beforeEach(() => {
        wrapper = mount(MountTarget, {
            propsData: {
                allowUserCreation: false,
                sessionCsrfToken: "sessionCsrfToken",
            },
            localVue,
        });
    });

    it("switching between register and login", async () => {
        const cardHeader = wrapper.find(".card-header");
        expect(cardHeader.text()).toBe("Welcome to Galaxy, please log in");
        const $registerToggle = "[id=register-toggle]";
        const missingToggle = wrapper.find($registerToggle);
        expect(missingToggle.exists()).toBeFalsy();
        await wrapper.setProps({ allowUserCreation: true });
        const registerToggle = wrapper.find($registerToggle);
        expect(registerToggle.exists()).toBeTruthy();
        await registerToggle.trigger("click");
        expect(mockPush).toHaveBeenCalledWith("/register/start");
        expect(mockPush).toHaveBeenCalledTimes(1);
    });
});
