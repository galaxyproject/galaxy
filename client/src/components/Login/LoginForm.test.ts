import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/jest/helpers";
import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";

import { useServerMock } from "@/api/client/__mocks__";
import { HttpResponse } from "@/api/client/__mocks__/index";

import MountTarget from "./LoginForm.vue";

const localVue = getLocalVue(true);
const testingPinia = createTestingPinia({ stubActions: false });

const { server, http } = useServerMock();

async function mountLoginForm() {
    const wrapper = mount(MountTarget as object, {
        propsData: {
            sessionCsrfToken: "sessionCsrfToken",
        },
        localVue,
        stubs: {
            ExternalLogin: true,
        },
        pinia: testingPinia,
    });

    return wrapper;
}

describe("LoginForm", () => {
    let axiosMock: MockAdapter;

    beforeEach(() => {
        axiosMock = new MockAdapter(axios);
        server.use(
            http.get("/api/configuration", ({ response }) => {
                return response.untyped(HttpResponse.json({ oidc: { cilogon: false, custos: false } }));
            })
        );
    });

    afterEach(() => {
        axiosMock.reset();
    });

    it("basics", async () => {
        const wrapper = await mountLoginForm();

        const cardHeader = wrapper.find(".card-header");
        expect(cardHeader.text()).toBe("Welcome to Galaxy, please log in");

        const inputs = wrapper.findAll("input");
        expect(inputs.length).toBe(2);

        const usernameField = inputs.at(0);
        expect(usernameField.attributes("type")).toBe("text");

        await usernameField.setValue("test_user");

        const pwdField = inputs.at(1);
        expect(pwdField.attributes("type")).toBe("password");

        await pwdField.setValue("test_pwd");

        const submitButton = wrapper.find("button[type='submit']");
        await submitButton.trigger("submit");

        const postedData = JSON.parse(axiosMock.history.post?.[0]?.data);
        expect(postedData.login).toBe("test_user");
        expect(postedData.password).toBe("test_pwd");
    });

    it("props", async () => {
        const wrapper = await mountLoginForm();

        const $register = "#register-toggle";
        expect(wrapper.findAll($register).length).toBe(0);

        await wrapper.setProps({
            allowUserCreation: true,
            enableOidc: true,
            showWelcomeWithLogin: true,
            welcomeUrl: "welcome_url",
        });

        const register = wrapper.find($register);
        (expect(register.text()) as any).toBeLocalizationOf("Register here.");

        const welcomePage = wrapper.find("iframe");
        expect(welcomePage.attributes("src")).toBe("welcome_url");
        await flushPromises();
    });

    it("connect external provider", async () => {
        const external_email = "test@test.com";
        const provider_id = "test_provider";
        const provider_label = "Provider";

        const originalLocation = window.location;
        jest.spyOn(window, "location", "get").mockImplementation(() => ({
            ...originalLocation,
            search: `?connect_external_email=${external_email}&connect_external_provider=${provider_id}&connect_external_label=${provider_label}`,
        }));

        const wrapper = await mountLoginForm();

        expect(wrapper.find(".card-header").exists()).toBe(false);

        const alert = wrapper.find(".alert");
        expect(alert.classes()).toContain("alert-info");
        expect(alert.text()).toContain(`There already exists a user with the email ${external_email}`);
        expect(alert.text()).toContain(`In order to associate this account with ${provider_label}`);

        const inputs = wrapper.findAll("input");
        expect(inputs.length).toBe(2);

        const usernameField = inputs.at(0);
        expect(usernameField.attributes("type")).toBe("text");
        expect((usernameField.element as HTMLInputElement).disabled).toBe(true);
        expect((usernameField.element as HTMLInputElement).value).not.toBe("");
        expect((usernameField.element as HTMLInputElement).value).toContain(external_email);

        const pwdField = inputs.at(1);
        expect(pwdField.attributes("type")).toBe("password");
        expect((pwdField.element as HTMLInputElement).value).toBe("");

        await pwdField.setValue("test_pwd");

        const submitButton = wrapper.find("button[type='submit']");

        await submitButton.trigger("submit");

        const postedData = JSON.parse(axiosMock.history.post?.[0]?.data);
        expect(postedData.login).toBe(external_email);
        expect(postedData.password).toBe("test_pwd");

        const postedURL = axiosMock.history.post?.[0]?.url;
        expect(postedURL).toBe("/user/login");
        await flushPromises();
    });
});
