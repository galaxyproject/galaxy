import { createTestingPinia } from "@pinia/testing";
import { createTestRouter, getLocalVue, nth, withPlugins } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { sanitizeHtml } from "@/directives/sanitizeHtml";

import LoginForm from "./LoginForm.vue";

const localVue = getLocalVue(true);
const router = createTestRouter();
const testingPinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });

const { server, http } = useServerMock();

const SELECTORS = {
    ALERT: ".alert",
    CARD_HEADER: ".card-header",
    EXTERNAL_LOGIN: "external-login-stub",
    LOGIN_INPUT: "#login-form-name",
    PASSWORD_INPUT: "#login-form-password",
    SUBMIT_BUTTON: "button[type='submit']",
    RESET_PASSWORD_LINK: "#reset-password-link",
    REGISTER_TOGGLE: "#register-toggle",
    REGISTRATION_DISABLED: "[data-description='registration disabled message']",
    WELCOME_PAGE: "iframe",
};

interface LoginRequest {
    url: string;
    data: Record<string, unknown>;
}

let loginRequests: LoginRequest[] = [];
let loginResponse: Record<string, unknown> = {};

function mountLoginForm(props: Record<string, unknown> = {}) {
    return mount(LoginForm, {
        props: {
            sessionCsrfToken: "sessionCsrfToken",
            ...props,
        },
        global: {
            ...withPlugins(localVue, testingPinia, router),
            stubs: { ...localVue.stubs, ExternalLogin: true },
        },
    });
}

/** LoginForm reads the query once, at setup; vitest-location-mock resets `window.location` before each test. */
function visitLoginPage(query: string) {
    window.location.href = `${window.location.origin}/login/start?${query}`;
}

function stubRouterPush() {
    return vi.spyOn(router, "push").mockImplementation(async () => {});
}

describe("LoginForm", () => {
    beforeEach(() => {
        loginRequests = [];
        loginResponse = {};
        server.use(
            http.get("/api/configuration", ({ response }) => {
                return response.untyped(HttpResponse.json({ oidc: { cilogon: false } }));
            }),
            http.untyped.post(/.*\/user\/login.*/, async ({ request }) => {
                const data = (await request.json()) as Record<string, unknown>;
                loginRequests.push({ url: request.url, data });
                return HttpResponse.json(loginResponse);
            }),
        );
    });

    it("submits new account confirmation with the session CSRF token", async () => {
        let confirmationBody: URLSearchParams | undefined;
        server.use(
            http.untyped.post(/.*\/authnz\/keycloak\/create_user$/, async ({ request }) => {
                confirmationBody = new URLSearchParams(await request.text());
                return HttpResponse.json({ redirect_uri: "/" });
            }),
        );
        const navigate = vi.spyOn(window.location, "assign").mockImplementation(() => {});
        const previousSearch = window.location.search;
        Object.defineProperty(window.location, "search", {
            configurable: true,
            writable: true,
            value: "?confirm=true&provider=keycloak&confirmation_id=pending",
        });
        try {
            const wrapper = await mountLoginForm();
            await flushPromises();
            await wrapper.find("input[type='checkbox']").setValue(true);
            await wrapper.find("button[name='confirm']").trigger("click");
            await flushPromises();
            expect(confirmationBody?.get("session_csrf_token")).toBe("sessionCsrfToken");
            expect(confirmationBody?.get("confirmation_id")).toBe("pending");
            wrapper.unmount();
        } finally {
            navigate.mockRestore();
            Object.defineProperty(window.location, "search", {
                configurable: true,
                writable: true,
                value: previousSearch,
            });
        }
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("posts the entered name and password to the login endpoint", async () => {
        const wrapper = mountLoginForm();

        expect(wrapper.find(SELECTORS.CARD_HEADER).text()).toBe("Welcome to Galaxy, please log in");
        const inputs = wrapper.findAll("input");
        expect(inputs.length).toBe(2);
        const usernameField = nth(inputs, 0);
        const passwordField = nth(inputs, 1);
        expect(usernameField.attributes("type")).toBe("text");
        expect(passwordField.attributes("type")).toBe("password");

        await usernameField.setValue("test_user");
        await passwordField.setValue("test_pwd");
        await wrapper.find(SELECTORS.SUBMIT_BUTTON).trigger("submit");
        await flushPromises();

        expect(loginRequests.length).toBe(1);
        expect(loginRequests[0]?.data.login).toBe("test_user");
        expect(loginRequests[0]?.data.password).toBe("test_pwd");
    });

    it("prefills the password reset route with the entered email", async () => {
        const push = stubRouterPush();
        const wrapper = mountLoginForm({ showResetLink: true });

        await wrapper.find(SELECTORS.LOGIN_INPUT).setValue("test@example.com");
        await wrapper.find(SELECTORS.RESET_PASSWORD_LINK).trigger("click");

        expect(push).toHaveBeenCalledWith({
            path: "/login/reset_password",
            query: { email: "test@example.com" },
        });
    });

    it("routes expired-password responses to the current-password form", async () => {
        loginResponse = { expired_user: "expired-user-id" };
        const push = stubRouterPush();
        const wrapper = mountLoginForm();

        await wrapper.find(SELECTORS.LOGIN_INPUT).setValue("test_user");
        await wrapper.find(SELECTORS.PASSWORD_INPUT).setValue("test_pwd");
        await wrapper.find(SELECTORS.SUBMIT_BUTTON).trigger("submit");
        await flushPromises();

        expect(push).toHaveBeenCalledWith({
            path: "/login/start",
            query: { expired_user: "expired-user-id" },
        });
    });

    it("says registration is disabled when user creation is off", () => {
        const wrapper = mountLoginForm();

        expect(wrapper.find(SELECTORS.REGISTRATION_DISABLED).exists()).toBe(true);
        expect(wrapper.find(SELECTORS.REGISTER_TOGGLE).exists()).toBe(false);
    });

    it("shows the register link, external login and welcome page once they are enabled", async () => {
        const wrapper = mountLoginForm();

        await wrapper.setProps({
            allowUserCreation: true,
            enableOidc: true,
            showWelcomeWithLogin: true,
            welcomeUrl: "welcome_url",
        });

        expect(wrapper.find(SELECTORS.REGISTRATION_DISABLED).exists()).toBe(false);
        const registerToggle = wrapper.find(SELECTORS.REGISTER_TOGGLE);
        expect(registerToggle.text()).toBe("Register here.");
        expect(registerToggle.attributes("href")).toBe("/register/start");
        expect(wrapper.find(SELECTORS.EXTERNAL_LOGIN).exists()).toBe(true);
        expect(wrapper.find(SELECTORS.WELCOME_PAGE).attributes("src")).toBe("welcome_url");
    });

    it("hides the register link when local accounts are disabled", async () => {
        const wrapper = mountLoginForm();

        await wrapper.setProps({
            allowUserCreation: true,
            disableLocalAccounts: true,
        });

        expect(wrapper.find(SELECTORS.REGISTER_TOGGLE).exists()).toBe(false);
        expect(wrapper.find(SELECTORS.REGISTRATION_DISABLED).exists()).toBe(true);
    });

    it("logs in as the existing account's email when connecting an external provider", async () => {
        const externalEmail = "test@test.com";
        const providerLabel = "Provider";
        visitLoginPage(
            `connect_external_email=${externalEmail}&connect_external_provider=test_provider&connect_external_label=${providerLabel}`,
        );

        const wrapper = mountLoginForm();

        expect(wrapper.find(SELECTORS.CARD_HEADER).exists()).toBe(false);
        const alert = wrapper.find(SELECTORS.ALERT);
        expect(alert.classes()).toContain("alert-info");
        expect(alert.text()).toContain(`There already exists a user with the email ${externalEmail}`);
        expect(alert.text()).toContain(`In order to associate this account with ${providerLabel}`);

        const inputs = wrapper.findAll("input");
        expect(inputs.length).toBe(2);
        const usernameField = nth(inputs, 0);
        const usernameInput = usernameField.element as HTMLInputElement;
        expect(usernameField.attributes("type")).toBe("text");
        expect(usernameInput.disabled).toBe(true);
        expect(usernameInput.value).not.toBe("");
        expect(usernameInput.value).toContain(externalEmail);
        const passwordField = nth(inputs, 1);
        expect(passwordField.attributes("type")).toBe("password");
        expect((passwordField.element as HTMLInputElement).value).toBe("");

        await passwordField.setValue("test_pwd");
        await wrapper.find(SELECTORS.SUBMIT_BUTTON).trigger("submit");
        await flushPromises();

        expect(loginRequests.length).toBe(1);
        expect(loginRequests[0]?.data.login).toBe(externalEmail);
        expect(loginRequests[0]?.data.password).toBe("test_pwd");
        expect(loginRequests[0]?.url).toContain("/user/login");
    });

    it("renders the message and status from the query string", async () => {
        visitLoginPage("message=auth-error&status=info");

        const wrapper = mountLoginForm();
        await flushPromises();

        const alert = wrapper.find(SELECTORS.ALERT);
        expect(alert.exists()).toBe(true);
        expect(alert.text()).toContain("auth-error");
        expect(alert.classes()).toContain("alert-info");
    });

    it("renders the message through v-sanitize-html", async () => {
        visitLoginPage(`message=${encodeURIComponent("<b>note</b>")}`);
        vi.mocked(sanitizeHtml).mockClear();

        const wrapper = mountLoginForm();
        await flushPromises();

        expect(sanitizeHtml).toHaveBeenCalledWith("<b>note</b>", "default");
        expect(wrapper.find(`${SELECTORS.ALERT} b`).text()).toBe("note");
    });
});
