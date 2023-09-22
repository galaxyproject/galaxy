import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import FormElement from "./FormElement";
import FormHidden from "./Elements/FormHidden";
import FormText from "./Elements/FormText";

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
        expect(title.text()).toContain("title_text");
    });

    it("check collapsibles and other features", async () => {
        await wrapper.setProps({ disabled: true });
        expect(wrapper.findAll(".ui-form-field").length).toEqual(0);

        await wrapper.setProps({ disabled: false });
        expect(wrapper.findAll(".ui-form-field").length).toEqual(1);

        await wrapper.setProps({
            attributes: { default_value: "default_value", collapsible_value: "collapsible_value" },
        });
        expect(wrapper.find(".ui-form-title-text").text()).toEqual("title_text");
        expect(wrapper.findAll("button[title='Disable']").length).toEqual(1);

        await wrapper.find(".ui-form-collapsible-icon").trigger("click");
        expect(wrapper.emitted().input[0][0]).toEqual("collapsible_value");
        expect(wrapper.emitted().input[0][1]).toEqual("input");

        await wrapper.setProps({
            collapsedEnableText: "Enable Collapsible",
            collapsedDisableText: "Disable Collapsible",
        });
        expect(wrapper.findAll("button[title='Enable Collapsible']").length).toEqual(1);
        expect(wrapper.findAll("button[title='Disable Collapsible']").length).toEqual(0);

        await wrapper.find(".ui-form-collapsible-icon").trigger("click");
        expect(wrapper.emitted().input[1][0]).toEqual("default_value");
        expect(wrapper.findAll("button[title='Disable Collapsible']").length).toEqual(1);
        expect(wrapper.findAll("button[title='Enable Collapsible']").length).toEqual(0);
    });

    it("check type matching", async () => {
        await wrapper.setProps({ type: "text" });
        expect(wrapper.findComponent(FormText).exists()).toBe(true);
        expect(wrapper.findComponent(FormHidden).exists()).toBe(false);

        await wrapper.setProps({ attributes: { titleonly: true } });
        expect(wrapper.findComponent(FormHidden).exists()).toBe(true);
        expect(wrapper.findComponent(FormText).exists()).toBe(false);
    });

    it("displays as the correct type if is_workflow is true", async () => {
        await wrapper.setProps({ type: "data_column", attributes: { is_workflow: true } });
        expect(wrapper.findComponent(FormText).exists()).toBe(true);
    });

    it("marks required values", async () => {
        await wrapper.setProps({ type: "text", attributes: { optional: false } });
        expect(wrapper.find(".ui-form-title-star").exists()).toBe(true);
        expect(wrapper.find(".ui-form-title-message").exists()).toBe(false);
    });

    it("marks optional values", async () => {
        await wrapper.setProps({ type: "text", attributes: { optional: true } });
        expect(wrapper.find(".ui-form-title-star").exists()).toBe(false);
        expect(wrapper.find(".ui-form-title-message").text()).toContain("optional");
    });

    it("warns about empty required values", async () => {
        await wrapper.setProps({ type: "text", value: "", attributes: { optional: false } });
        expect(wrapper.find(".ui-form-title-star").exists()).toBe(true);
        expect(wrapper.find(".ui-form-title-message").text()).toContain("required");
    });
});
