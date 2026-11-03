import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import { setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { LocationQuery } from "vue-router";

import { resetMockConfig, setMockConfig } from "@/composables/__mocks__/config";

import Login from "./Login.vue";
import ChangePassword from "@/components/Login/ChangePassword.vue";
import LoginIndex from "@/components/Login/LoginIndex.vue";

enableAutoUnmount(afterEach);

vi.mock("@/app/index", () => ({
    getGalaxyInstance: vi.fn(() => ({ session_csrf_token: "session_csrf_token" })),
}));

vi.mock("@/composables/config");

// Login reads useRoute() directly, so provide its query through the composable mock.
let currentRouteQuery: LocationQuery = {};
vi.mock("vue-router", () => ({
    useRoute: () => ({ query: currentRouteQuery }),
}));

beforeEach(() => {
    resetMockConfig();
    setMockConfig({
        allow_local_account_creation: true,
        enable_oidc: true,
        mailing_join_addr: "mailing_join_addr",
        prefer_oidc_login: true,
        registration_warning_message: "registration_warning_message",
        server_mail_configured: true,
        show_welcome_with_login: true,
        terms_url: "terms_url",
        welcome_url: "welcome_url",
    });
});

function shallowMountLogin(routerQuery: LocationQuery = {}) {
    currentRouteQuery = routerQuery;

    const pinia = createTestingPinia({ createSpy: vi.fn });
    setActivePinia(pinia);

    return shallowMount(Login, {
        global: getLocalVue(true),
        pinia,
    });
}

describe("Login", () => {
    it("passes configuration, redirect, and CSRF token to the login form", () => {
        const wrapper = shallowMountLogin({
            redirect: "redirect_url",
        });

        const loginForm = wrapper.getComponent(LoginIndex);
        expect(loginForm.attributes("id")).toBe("login-index");
        expect(loginForm.props()).toMatchObject({
            allowUserCreation: true,
            enableOidc: true,
            redirect: "redirect_url",
            registrationWarningMessage: "registration_warning_message",
            sessionCsrfToken: "session_csrf_token",
            showWelcomeWithLogin: true,
            termsUrl: "terms_url",
            welcomeUrl: "welcome_url",
        });
    });

    it("passes the password reset query to the change-password form", () => {
        const wrapper = shallowMountLogin({
            token: "test_token",
            status: "test_status",
            message: "test_message",
            expired_user: "test_user",
        });

        const changePasswordForm = wrapper.getComponent(ChangePassword);
        expect(changePasswordForm.attributes("id")).toBe("change-password");
        expect(changePasswordForm.props()).toMatchObject({
            token: "test_token",
            expiredUser: "test_user",
            messageText: "test_message",
            messageVariant: "test_status",
        });
    });
});
