import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import FormElement from "./FormElement";

const localVue = getLocalVue();

describe("FormElement", () => {
    let wrapper;

    beforeEach(() => {
        wrapper = mount(FormElement, {
            propsData: {
                id: "input",
                value: "initial_value",
                help: "help_text",
                error: "error_text",
                title: "title_text",
            },
            localVue,
        });
    });

    it("check props", async () => {
        const help = wrapper.find(".ui-form-info");
        expect(help.text()).toBe("help_text");
        const error = wrapper.find(".ui-form-error-text");
        expect(error.text()).toBe("error_text");
        await wrapper.setProps({ error: "" });
        const no_error = wrapper.findAll(".ui-form-error");
        expect(no_error.length).toBe(0);
        const title = wrapper.find(".ui-form-title");
        expect(title.text()).toBe("title_text");
    });
});
