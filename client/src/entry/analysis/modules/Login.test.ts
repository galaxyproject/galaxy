import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/jest/helpers";
import { shallowMount } from "@vue/test-utils";
import { setActivePinia } from "pinia";

import { getGalaxyInstance } from "@/app/singleton";

import Login from "./Login.vue";

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

function shallowMountLogin(routerQuery: object = {}) {
    const pinia = createTestingPinia();
    setActivePinia(pinia);

    return shallowMount(Login, {
        localVue,
        pinia,
        mocks: {
            $router: mockRouter(routerQuery),
        },
    });
}

describe("Login", () => {
    it("login index attribute matching", async () => {
        const wrapper = shallowMountLogin({
            redirect: "redirect_url",
        });

        const attributes = wrapper.find("#login-index").attributes();

        expect(attributes.redirect).toBe("redirect_url");
        expect(attributes.allowusercreation).toBe("true");
        expect(attributes.sessioncsrftoken).toBe("session_csrf_token");
        expect(attributes.enableoidc).toBe("true");
        expect(attributes.mailingjoinaddr).toBe("mailing_join_addr");
        expect(attributes.prefercustoslogin).toBe("true");
        expect(attributes.servermailconfigured).toBe("true");
        expect(attributes.showwelcomewithlogin).toBe("true");
        expect(attributes.registrationwarningmessage).toBe("registration_warning_message");
        expect(attributes.termsurl).toBe("terms_url");
        expect(attributes.welcomeurl).toBe("welcome_url");
    });

    it("change password attribute matching", async () => {
        const wrapper = shallowMountLogin({
            token: "test_token",
            status: "test_status",
            message: "test_message",
            expired_user: "test_user",
        });

        const attributes = wrapper.find("#change-password").attributes();
        expect(attributes.token).toBe("test_token");
        expect(attributes.expireduser).toBe("test_user");
        expect(attributes.messagetext).toBe("test_message");
        expect(attributes.messagevariant).toBe("test_status");
    });
});
