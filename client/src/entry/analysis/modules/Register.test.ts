import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import { resetMockConfig, setMockConfig } from "@/composables/__mocks__/config";

import Register from "./Register.vue";
import RegisterForm from "@/components/Register/RegisterForm.vue";

vi.mock("@/app/index", () => ({
    getGalaxyInstance: vi.fn(() => ({ session_csrf_token: "session_csrf_token" })),
}));
vi.mock("@/composables/config");

enableAutoUnmount(afterEach);
afterEach(resetMockConfig);

describe("Register", () => {
    it("passes the session token and registration configuration to the form", () => {
        setMockConfig({
            enable_oidc: true,
            mailing_join_addr: "mailing_join_addr",
            prefer_oidc_login: true,
            registration_warning_message: "registration_warning_message",
            server_mail_configured: true,
            terms_url: "terms_url",
        });
        const wrapper = shallowMount(Register, { global: getLocalVue(true) });

        expect(wrapper.getComponent(RegisterForm).props()).toMatchObject({
            sessionCsrfToken: "session_csrf_token",
            enableOidc: true,
            mailingJoinAddr: "mailing_join_addr",
            preferOidcLogin: true,
            serverMailConfigured: true,
            registrationWarningMessage: "registration_warning_message",
            termsUrl: "terms_url",
        });
    });
});
