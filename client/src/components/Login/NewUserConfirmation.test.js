import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import MountTarget from "./NewUserConfirmation";

const localVue = getLocalVue(true);

describe("NewUserConfirmation", () => {
    let wrapper;
    let axiosMock;

    beforeEach(() => {
        axiosMock = new MockAdapter(axios);
        wrapper = mount(MountTarget, {
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
        expect(axiosMock.history.post.length).toBe(0);
        await checkField.setChecked();
        await submitButton.trigger("click");
        const postedData = axiosMock.history.post[0];
        expect(postedData.url).toBe("/authnz/custos/create_user?token=null");
        await wrapper.setProps({ registrationWarningMessage: "registration warning message" });
        const alert = wrapper.find(".alert");
        expect(alert.text()).toBe("registration warning message");
        await wrapper.setProps({ termsUrl: "terms_url" });
        const termsFrame = wrapper.find("iframe");
        expect(termsFrame.attributes("src")).toBe("terms_url");
        const $toggle = "a[id=login-toggle]";
        const loginToggle = wrapper.find($toggle);
        expect(loginToggle.text()).toBe("Log in here.");
    });
});
