import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/jest/helpers";
import { shallowMount } from "@vue/test-utils";

import { getGalaxyInstance } from "@/app/singleton";

import Register from "./Register.vue";
import RegisterForm from "@/components/Register/RegisterForm.vue";

const localVue = getLocalVue(true);

const configMock = {
    allow_local_account_creation: true,
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

function shallowMountRegister(routerQuery: object = {}) {
    const pinia = createTestingPinia();

    return shallowMount(Register as object, {
        localVue,
        pinia,
        mocks: {
            $router: mockRouter(routerQuery),
        },
    });
}

describe("Register", () => {
    it("Register component prop matching", async () => {
        const wrapper = shallowMountRegister({
            redirect: "redirect_url",
        });

        const props = wrapper.findComponent(RegisterForm).props();

        expect(props.sessionCsrfToken).toBe("session_csrf_token");
        expect(props.enableOidc).toBe(true);
        expect(props.mailingJoinAddr).toBe("mailing_join_addr");
        expect(props.preferCustosLogin).toBe(true);
        expect(props.serverMailConfigured).toBe(true);
        expect(props.registrationWarningMessage).toBe("registration_warning_message");
        expect(props.termsUrl).toBe("terms_url");
    });
});
