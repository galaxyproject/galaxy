import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/jest/helpers";
import { mount } from "@vue/test-utils";
import { setActivePinia } from "pinia";

import { getGalaxyInstance } from "@/app/singleton";

import ResetPassword from "./ResetPassword.vue";
import assert from "assert";

const localVue = getLocalVue(true);

const configMock = {
    allow_user_creation: true,
    enable_oidc: true,
    mailing_join_addr: "mailing_join_addr",
    prefer_custos_login: true,
    registration_warning_message: "registration_warning_message",
    server_mail_configured: true,
    show_welcome_with_login: true,
    terms_url: "terms_url",
    welcome_url: "welcome_url",
};

jest.mock("app/singleton");
jest.mock("@/composables/config", () => ({
    useConfig: jest.fn(() => ({
        config: configMock,

        isConfigLoaded: true,
    })),
}));

const mockRouter = (query: object) => ({
    currentRoute: {
        query,
    },
});

(getGalaxyInstance as jest.Mock).mockReturnValue({ session_csrf_token: "session_csrf_token" });

function mountResetPassword(routerQuery: object = {}) {
    const pinia = createTestingPinia();
    setActivePinia(pinia);

    return mount(ResetPassword, {
        localVue,
        pinia,
        mocks: {
            $router: mockRouter(routerQuery),
        },
    });
}

describe("ResetPassword", () => {
    it("ResetPassword index attribute matching", async () => {
        const wrapper = mountResetPassword({
            redirect: "redirect_url",
        });
        const emailField = wrapper.find("#reset-email");
        const submitButton = wrapper.find("#reset-password");
        const testEmail = "eihfeuh";

        emailField.setValue(testEmail);
        const emailValue = emailField.element.textContent;
        expect(emailValue).toBe(testEmail);

    });
});
