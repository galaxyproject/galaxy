import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import { withPrefix } from "utils/redirect";
import MountTarget from "./ChangePassword";

// mock routes
jest.mock("utils/redirect");
const mockSafePath = jest.fn();
withPrefix.mockImplementation(() => mockSafePath);

const localVue = getLocalVue(true);

describe("ChangePassword", () => {
    let wrapper;
    let axiosMock;

    beforeEach(() => {
        axiosMock = new MockAdapter(axios);
        wrapper = mount(MountTarget, {
            propsData: {
                messageText: "message_text",
                messageVariant: "message_variant",
            },
            localVue,
        });
    });

    afterEach(() => {
        axiosMock.reset();
    });

    it("basics", async () => {
        const cardHeader = wrapper.find(".card-header");
        expect(cardHeader.text()).toBe("Change your password");
        const inputs = wrapper.findAll("input");
        expect(inputs.length).toBe(2);
        const firstPwdField = inputs.at(0);
        expect(firstPwdField.attributes("type")).toBe("password");
        await firstPwdField.setValue("test_first_pwd");
        const secondPwdField = inputs.at(1);
        expect(secondPwdField.attributes("type")).toBe("password");
        await secondPwdField.setValue("test_second_pwd");
        const submitButton = wrapper.find("button[type='submit']");
        await submitButton.trigger("submit");
        const postedData = JSON.parse(axiosMock.history.post[0].data);
        expect(postedData.password).toBe("test_first_pwd");
        expect(postedData.confirm).toBe("test_second_pwd");
    });

    it("props", async () => {
        await wrapper.setProps({
            token: "test_token",
            expiredUser: "expired_user",
        });
        const input = wrapper.find("input");
        expect(input.attributes("type")).toBe("password");
        await input.setValue("current_password");
        const submitButton = wrapper.find("button[type='submit']");
        await submitButton.trigger("submit");
        const postedData = JSON.parse(axiosMock.history.post[0].data);
        expect(postedData.token).toBe("test_token");
        expect(postedData.id).toBe("expired_user");
        expect(postedData.current).toBe("current_password");
        const alert = wrapper.find(".alert");
        expect(alert.text()).toBe("message_text");
    });
});
