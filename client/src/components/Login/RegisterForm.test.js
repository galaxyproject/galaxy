import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import MountTarget from "./RegisterForm";

const localVue = getLocalVue(true);

describe("RegisterForm", () => {
    let wrapper;
    let axiosMock;

    beforeEach(() => {
        axiosMock = new MockAdapter(axios);
        wrapper = mount(MountTarget, {
            propsData: {
                sessionCsrfToken: "sessionCsrfToken",
            },
            localVue,
        });
    });

    afterEach(() => {
        axiosMock.reset();
    });

    it("basics", async () => {
        const cardHeader = wrapper.find(".card-header");
        expect(cardHeader.text()).toBeLocalizationOf("Create a Galaxy account");
        const inputs = wrapper.findAll("input");
        expect(inputs.length).toBe(4);
        const usernameField = inputs.at(0);
        expect(usernameField.attributes("type")).toBe("text");
        await usernameField.setValue("test_user");
        const pwdField = inputs.at(1);
        expect(pwdField.attributes("type")).toBe("password");
        await pwdField.setValue("test_pwd");
        const submitButton = wrapper.find("button[type='submit']");
        await submitButton.trigger("submit");
        const postedData = JSON.parse(axiosMock.history.post[0].data);
        expect(postedData.email).toBe("test_user");
        expect(postedData.password).toBe("test_pwd");
    });
});
