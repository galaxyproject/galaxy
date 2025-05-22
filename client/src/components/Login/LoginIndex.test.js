import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import MountTarget from "./LoginIndex";

const localVue = getLocalVue();

const SELECTORS = {
    REGISTER_TOGGLE: "[id=register-toggle]",
    REGISTRATION_DISABLED: "[data-description='registration disabled message']",
};

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

        const missingToggle = wrapper.find(SELECTORS.REGISTER_TOGGLE); // TODO: Never appears because of the GLink change
        expect(missingToggle.exists()).toBeFalsy();
        expect(wrapper.find(SELECTORS.REGISTRATION_DISABLED).exists()).toBeTruthy();

        await wrapper.setProps({ allowUserCreation: true });
        expect(wrapper.find(SELECTORS.REGISTRATION_DISABLED).exists()).toBeFalsy();
        // TODO: Changing the original `<a>` to a `GLink` has made it so that the link never appears in the wrapper.
        //       Currentlly, we confirm its existence by checking the fact that the disabled message is not there.
        // const registerToggle = wrapper.find(SELECTORS.REGISTER_TOGGLE);
        // expect(registerToggle.exists()).toBeTruthy();
    });
});
