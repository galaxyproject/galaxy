import { getLocalVue } from "@tests/jest/helpers";
import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";

import ResetPassword from "./ResetPassword.vue";

const localVue = getLocalVue(true);

const mockRouter = (query: object) => ({
    currentRoute: {
        query,
    },
});

function mountResetPassword(routerQuery: object = {}) {
    return mount(ResetPassword, {
        localVue,
        attachTo: document.body,
        mocks: {
            $router: mockRouter(routerQuery),
        },
    });
}

describe("ResetPassword", () => {
    it("query", async () => {
        const email = "test";
        const wrapper = mountResetPassword({ email: "test" });

        const emailField = wrapper.find("#reset-email");
        const emailValue = (emailField.element as HTMLInputElement).value;
        expect(emailValue).toBe(email);
    });

    it("button text", async () => {
        const wrapper = mountResetPassword();
        const submitButton = wrapper.find("#reset-password");
        (expect(submitButton.text()) as any).toBeLocalizationOf("Send password reset email");
    });

    it("validate email", async () => {
        const wrapper = mountResetPassword();
        const submitButton = wrapper.find("#reset-password");
        const emailField = wrapper.find("#reset-email");
        const emailElement = emailField.element as HTMLInputElement;

        let email = "";
        await emailField.setValue(email);
        expect(emailElement.value).toBe(email);
        await submitButton.trigger("click");
        expect(emailElement.checkValidity()).toBe(false);

        email = "test";
        await emailField.setValue(email);
        expect(emailElement.value).toBe(email);
        await submitButton.trigger("click");
        expect(emailElement.checkValidity()).toBe(false);

        email = "test@test.com";
        await emailField.setValue(email);
        expect(emailElement.value).toBe(email);
        await submitButton.trigger("click");
        expect(emailElement.checkValidity()).toBe(true);
    });

    it("display success message", async () => {
        const wrapper = mountResetPassword({ email: "test@test.com" });
        const mockAxios = new MockAdapter(axios);
        const submitButton = wrapper.find("#reset-password");

        mockAxios.onPost("/user/reset_password").reply(200, {
            message: "Reset link has been sent to your email.",
        });
        await submitButton.trigger("click");
        setTimeout(async () => {
            const alertSuccess = wrapper.find("#reset-password-alert");
            expect(alertSuccess.text()).toBe("Reset link has been sent to your email.");
        });
    });

    it("display error message", async () => {
        const wrapper = mountResetPassword({ email: "test@test.com" });
        const submitButton = wrapper.find("#reset-password");

        const mockAxios = new MockAdapter(axios);
        mockAxios.onPost("/user/reset_password").reply(400, {
            err_msg: "Please provide your email.",
        });
        await submitButton.trigger("click");
        setTimeout(async () => {
            const alertError = wrapper.find("#reset-password-alert");
            expect(alertError.text()).toBe("Please provide your email.");
        });
    });
});
