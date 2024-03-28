import { getLocalVue } from "@tests/jest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";

import MountTarget from "./NewUserConfirmation.vue";

const localVue = getLocalVue(true);

const originalLocation = window.location;
jest.spyOn(window, "location", "get").mockImplementation(() => ({
    ...originalLocation,
    search: "?provider=test_provider&provider_token=sample_token",
}));

describe("NewUserConfirmation", () => {
    let wrapper: Wrapper<Vue>;
    let axiosMock: MockAdapter;

    beforeEach(() => {
        axiosMock = new MockAdapter(axios);
        wrapper = mount(MountTarget as object, {
            propsData: {},
            localVue,
        });
    });

    afterEach(() => {
        axiosMock.reset();
    });

    it("basics", async () => {
        const cardHeader = wrapper.find(".card-header");
        expect(cardHeader.text()).toBe("Confirm new account creation");

        const inputs = wrapper.findAll("input");
        expect(inputs.length).toBe(1);

        const checkField = inputs.at(0);
        expect(checkField.attributes("type")).toBe("checkbox");

        const submitButton = wrapper.find("button[name='confirm']");
        await submitButton.trigger("click");

        expect(axiosMock.history.post?.length).toBe(0);

        await checkField.setChecked();

        await submitButton.trigger("click");

        const postedData = axiosMock.history.post?.[0];
        expect(postedData?.url).toBe("/authnz/test_provider/create_user?token=sample_token");

        await wrapper.setProps({ registrationWarningMessage: "registration warning message" });

        const alert = wrapper.find(".alert");
        expect(alert.text()).toBe("registration warning message");

        await wrapper.setProps({ termsUrl: "terms_url" });

        const termsFrame = wrapper.find("iframe");
        expect(termsFrame.attributes("src")).toBe("terms_url");

        const toggle = "a[id=login-toggle]";
        const loginToggle = wrapper.find(toggle);
        expect(loginToggle.text()).toBe("Log in here.");
    });
});
