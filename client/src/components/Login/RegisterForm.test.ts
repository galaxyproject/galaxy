import { getLocalVue } from "@tests/jest/helpers";
import { mount, shallowMount, VueWrapper } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";

import MountTarget from "./RegisterForm.vue";

const localVue = getLocalVue(true);

describe("RegisterForm", () => {
    let wrapper: VueWrapper<any>;
    let axiosMock: MockAdapter;

    beforeEach(() => {
        axiosMock = new MockAdapter(axios);

        wrapper = mount(MountTarget as any, {
            props: {
                sessionCsrfToken: "sessionCsrfToken",
            },
            global: localVue.global,
        });
    });

    afterEach(() => {
        axiosMock.reset();
    });

    it("basics", async () => {
        const cardHeader = wrapper.find(".card-header");
        (expect(cardHeader.text()) as any).toBeLocalizationOf("Create a Galaxy account");

        const inputs = wrapper.findAll("input");
        expect(inputs.length).toBe(4);

        const usernameField = inputs[0]!;
        expect(usernameField.attributes("type")).toBe("text");
        await usernameField.setValue("test_user");

        const pwdField = inputs[1]!;
        expect(pwdField.attributes("type")).toBe("password");
        await pwdField.setValue("test_pwd");

        const submitButton = wrapper.find("button[type='submit']");
        await submitButton.trigger("submit");

        const postedData = JSON.parse(axiosMock.history.post?.[0]?.data);
        expect(postedData.email).toBe("test_user");
        expect(postedData.password).toBe("test_pwd");
    });
});
