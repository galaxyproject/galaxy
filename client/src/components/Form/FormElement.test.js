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
            stubs: {
                FormInput: { template: "<div>form-input</div>" },
                FormHidden: { template: "<div>form-hidden</div>" },
            },
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
        await wrapper.setProps({ default_value: "default_value", collapsible_value: "collapsible_value" });
        expect(wrapper.find(".ui-form-title-text").text()).toEqual("title_text");
        expect(wrapper.findAll("span[title='Disable']").length).toEqual(1);
        expect(wrapper.emitted().input[0][0]).toEqual("initial_value");
        await wrapper.find(".ui-form-collapsible-icon").trigger("click");
        expect(wrapper.emitted().input[1][0]).toEqual("collapsible_value");
        expect(wrapper.emitted().input[1][1]).toEqual("input");
        await wrapper.setProps({
            collapsedEnableText: "Enable Collapsible",
            collapsedDisableText: "Disable Collapsible",
        });
        expect(wrapper.findAll("span[title='Enable Collapsible']").length).toEqual(1);
        expect(wrapper.findAll("span[title='Disable Collapsible']").length).toEqual(0);
        await wrapper.find(".ui-form-collapsible-icon").trigger("click");
        expect(wrapper.emitted().input[2][0]).toEqual("default_value");
        expect(wrapper.findAll("span[title='Disable Collapsible']").length).toEqual(1);
        expect(wrapper.findAll("span[title='Enable Collapsible']").length).toEqual(0);
    });

    it("check type matching", async () => {
        await wrapper.setProps({ type: "text" });
        expect(wrapper.find("div[id='input'").text()).toEqual("form-input");
        await wrapper.setProps({ attributes: { titleonly: true } });
        expect(wrapper.find("div[id='input'").text()).toEqual("form-hidden");
    });
});
