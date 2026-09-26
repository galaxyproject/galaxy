import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import ResetPassword from "./ResetPassword.vue";

const localVue = getLocalVue(true);
const { server, http } = useServerMock();

const mockRouter = (query: object) => ({
    currentRoute: {
        query,
    },
});

function mountResetPassword(routerQuery: object = {}) {
    return mount(ResetPassword as object, {
        localVue,
        attachTo: document.body,
        mocks: {
            $router: mockRouter(routerQuery),
        },
    });
}

describe("ResetPassword", () => {
    it("prefills the email from the route query", () => {
        const email = "test@example.com";
        const wrapper = mountResetPassword({ email });

        const emailField = wrapper.find("#reset-email");
        const emailValue = (emailField.element as HTMLInputElement).value;
        expect(emailValue).toBe(email);
    });

    it("renders the localized submit label", () => {
        const wrapper = mountResetPassword();
        const submitButton = wrapper.find("#reset-password");
        (expect(submitButton.text()) as any).toBeLocalizationOf("Send password reset email");
    });

    it("uses native email validation", async () => {
        const wrapper = mountResetPassword();
        const emailField = wrapper.find("#reset-email");
        const emailElement = emailField.element as HTMLInputElement;

        await emailField.setValue("");
        expect(emailElement.checkValidity()).toBe(false);

        await emailField.setValue("test");
        expect(emailElement.checkValidity()).toBe(false);

        await emailField.setValue("test@example.com");
        expect(emailElement.checkValidity()).toBe(true);
    });

    it("displays the success response", async () => {
        server.use(
            http.untyped.post(/.*\/user\/reset_password.*/, () =>
                HttpResponse.json({ message: "Reset link has been sent to your email." }),
            ),
        );
        const wrapper = mountResetPassword({ email: "test@example.com" });

        await wrapper.find("form").trigger("submit");
        await flushPromises();

        expect(wrapper.find("#reset-password-alert").text()).toBe("Reset link has been sent to your email.");
    });

    it("displays an error response", async () => {
        server.use(
            http.untyped.post(/.*\/user\/reset_password.*/, () =>
                HttpResponse.json({ err_msg: "Please provide your email." }, { status: 400 }),
            ),
        );
        const wrapper = mountResetPassword({ email: "test@example.com" });

        await wrapper.find("form").trigger("submit");
        await flushPromises();

        expect(wrapper.find("#reset-password-alert").text()).toBe("Please provide your email.");
    });
});
