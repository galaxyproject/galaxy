import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import MountTarget from "./LoginIndex";

const globalConfig = getLocalVue(true);

describe("LoginIndex", () => {
    let wrapper;

    beforeEach(() => {
        wrapper = mount(MountTarget, {
            props: {
                allowUserCreation: false,
                sessionCsrfToken: "sessionCsrfToken",
            },
            global: globalConfig.global,
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
        const newCardHeader = wrapper.find(".card-header");
        expect(newCardHeader.text()).toBeLocalizationOf("Create a Galaxy account");
        const $loginToggle = "[id=login-toggle]";
        const loginToggle = wrapper.find($loginToggle);
        await loginToggle.trigger("click");
        const oldCardHeader = wrapper.find(".card-header");
        expect(oldCardHeader.text()).toBe("Welcome to Galaxy, please log in");
        expect(wrapper.vm.showLoginLink).toBe(true);
    });
});
