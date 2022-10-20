import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import flushPromises from "flush-promises";
import { safePath } from "utils/redirect";
import MountTarget from "./ChangePassword";

// mock routes
jest.mock("utils/redirect");
const mockSafePath = jest.fn();
safePath.mockImplementation(() => mockSafePath);

const localVue = getLocalVue(true);

describe("ChangePassword", () => {
    let wrapper;

    beforeEach(() => {
        wrapper = mount(MountTarget, {
            propsData: {
                expiredUser: "",
                token: "",
            },
            localVue,
        });
    });

    it("check props", async () => {
        await flushPromises();
        console.log(wrapper.html());
        const cardHeader = wrapper.find(".card-header");
        expect(cardHeader.text()).toBe("Change your password");
        const inputs = wrapper.findAll("input");
        expect(inputs.length).toBe(2);
        expect(inputs.at(0).attributes("type")).toBe("password");
        expect(inputs.at(1).attributes("type")).toBe("password");
    });
});
