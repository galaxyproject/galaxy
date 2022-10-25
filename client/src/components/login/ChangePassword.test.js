import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import { safePath } from "utils/redirect";
import MountTarget from "./ChangePassword";
import VueRouter from "vue-router";

// mock routes
jest.mock("utils/redirect");
const mockSafePath = jest.fn();
safePath.mockImplementation(() => mockSafePath);

const localVue = getLocalVue(true);
localVue.use(VueRouter);

const router = new VueRouter();

describe("ChangePassword", () => {
    let wrapper;
    let axiosMock;

    beforeEach(() => {
        axiosMock = new MockAdapter(axios);
        wrapper = mount(MountTarget, {
            propsData: {
                expiredUser: "",
                token: "",
            },
            localVue,
            router,
        });
    });

    afterEach(() => {
        axiosMock.reset();
    });

    it("basic tests", async () => {
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
});
