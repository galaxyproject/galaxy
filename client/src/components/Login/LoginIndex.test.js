import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import LoginIndex from "./LoginIndex.vue";

const localVue = getLocalVue();

const SELECTORS = {
    CARD_HEADER: ".card-header",
    REGISTER_TOGGLE: "#register-toggle",
    REGISTRATION_DISABLED: "[data-description='registration disabled message']",
};

function mountLoginIndex() {
    return mount(LoginIndex, {
        props: {
            allowUserCreation: false,
            sessionCsrfToken: "sessionCsrfToken",
        },
        global: localVue,
    });
}

describe("LoginIndex", () => {
    it("asks the user to log in and says registration is disabled when user creation is off", () => {
        const wrapper = mountLoginIndex();

        expect(wrapper.find(SELECTORS.CARD_HEADER).text()).toBe("Welcome to Galaxy, please log in");
        expect(wrapper.find(SELECTORS.REGISTRATION_DISABLED).exists()).toBe(true);
        expect(wrapper.find(SELECTORS.REGISTER_TOGGLE).exists()).toBe(false);
    });

    it("replaces the disabled message with a register link once user creation is allowed", async () => {
        const wrapper = mountLoginIndex();

        await wrapper.setProps({ allowUserCreation: true });

        expect(wrapper.find(SELECTORS.REGISTRATION_DISABLED).exists()).toBe(false);
        const registerToggle = wrapper.find(SELECTORS.REGISTER_TOGGLE);
        expect(registerToggle.text()).toBe("Register here.");
        expect(registerToggle.attributes("href")).toBe("/register/start");
    });
});
