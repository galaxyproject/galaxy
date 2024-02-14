import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
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
        expect(inputs.length).toBe(5);
        const emailField = inputs.at(0);
        expect(emailField.attributes("type")).toBe("text");
        await emailField.setValue("test_user@example.org");
        const pwdField = inputs.at(1);
        expect(pwdField.attributes("type")).toBe("password");
        await pwdField.setValue("test_pwd");
        const orcidIdField = inputs.at(4);
        expect(orcidIdField.attributes("type")).toBe("text");
        await orcidIdField.setValue("1111-2222-3333-4444");
        const submitButton = wrapper.find("button[type='submit']");
        await submitButton.trigger("submit");
        const postedData = JSON.parse(axiosMock.history.post[0].data);
        expect(postedData.email).toBe("test_user@example.org");
        expect(postedData.password).toBe("test_pwd");
        expect(postedData.orcidId).toBe("1111-2222-3333-4444");
    });
});
