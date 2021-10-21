import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import FormElement from "./FormElement";

jest.mock("app");

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

    it("check collapsibles and other features", async () => {
        await wrapper.setProps({ disabled: true });
        expect(wrapper.findAll(".ui-form-field").length).toEqual(0);
        await wrapper.setProps({ disabled: false });
        expect(wrapper.findAll(".ui-form-field").length).toEqual(1);
        await wrapper.setProps({ default_value: "second_value", collapsible_value: "collapsible_value" });
        expect(wrapper.find(".ui-form-collapsible-text").text()).toEqual("title_text");
        wrapper.find(".ui-form-collapsible-icon").trigger("click");
        expect(wrapper.emitted().input[0][0]).toEqual("collapsible_value");
        expect(wrapper.emitted().input[0][1]).toEqual("input");
    });
});
