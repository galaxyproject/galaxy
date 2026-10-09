import { emittedArg, getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import FormHidden from "./Elements/FormHidden.vue";
import FormNumber from "./Elements/FormNumber.vue";
import FormNumberList from "./Elements/FormNumberList.vue";
import FormText from "./Elements/FormText.vue";
import FormElement from "./FormElement.vue";

enableAutoUnmount(afterEach);

function mountElement(props = {}) {
    return mount(FormElement, {
        props: {
            id: "input",
            value: "initial_value",
            help: "help_text",
            error: "error_text",
            title: "title_text",
            ...props,
        },
        global: getLocalVue(),
    });
}

describe("FormElement", () => {
    it("renders help, error and title, then removes a cleared error", async () => {
        const wrapper = mountElement();
        const help = wrapper.find(".ui-form-info");
        expect(help.text()).toBe("help_text");

        const error = wrapper.find(".ui-form-error-text");
        expect(error.text()).toBe("error_text");

        await wrapper.setProps({ error: undefined });
        expect(wrapper.findAll(".ui-form-error")).toHaveLength(0);

        const title = wrapper.find(".ui-form-title");
        expect(title.text()).toContain("title_text");
    });

    it("hides and restores the field when disabled changes", async () => {
        const wrapper = mountElement({ disabled: true });
        expect(wrapper.findAll(".ui-form-field").length).toEqual(0);

        await wrapper.setProps({ disabled: false });
        expect(wrapper.findAll(".ui-form-field").length).toEqual(1);
    });

    it("collapses and restores values using custom button labels", async () => {
        const wrapper = mountElement({
            attributes: { default_value: "default_value", collapsible_value: "collapsible_value" },
        });
        expect(wrapper.find(".ui-form-title-text").text()).toEqual("title_text");
        expect(wrapper.findAll("button[data-title='Disable']").length).toEqual(1);

        await wrapper.find("[data-collapsible]").trigger("click");
        expect(emittedArg(wrapper, "input")).toEqual("collapsible_value");
        expect(wrapper.emitted("input")[0][1]).toEqual("input");

        await wrapper.setProps({
            collapsedEnableText: "Enable Collapsible",
            collapsedDisableText: "Disable Collapsible",
        });
        expect(wrapper.findAll("button[data-title='Enable Collapsible']").length).toEqual(1);
        expect(wrapper.findAll("button[data-title='Disable Collapsible']").length).toEqual(0);

        await wrapper.find("[data-collapsible]").trigger("click");
        expect(emittedArg(wrapper, "input", 1)).toEqual("default_value");
        expect(wrapper.findAll("button[data-title='Disable Collapsible']").length).toEqual(1);
        expect(wrapper.findAll("button[data-title='Enable Collapsible']").length).toEqual(0);
    });

    it("uses a hidden field when a text input becomes title-only", async () => {
        const wrapper = mountElement();
        await wrapper.setProps({ type: "text" });
        expect(wrapper.findComponent(FormText).exists()).toBe(true);
        expect(wrapper.findComponent(FormHidden).exists()).toBe(false);

        await wrapper.setProps({ attributes: { titleonly: true } });
        expect(wrapper.findComponent(FormHidden).exists()).toBe(true);
        expect(wrapper.findComponent(FormText).exists()).toBe(false);
    });

    it("renders workflow data columns as text fields", async () => {
        const wrapper = mountElement();
        await wrapper.setProps({ type: "data_column", attributes: { is_workflow: true } });
        expect(wrapper.findComponent(FormText).exists()).toBe(true);
    });

    it("switches multiple integers to one number field when multiple is cleared", async () => {
        const wrapper = mountElement();
        await wrapper.setProps({ type: "integer", value: [1, 2], workflowRun: true, attributes: { multiple: true } });
        expect(wrapper.findComponent(FormNumberList).exists()).toBe(true);
        expect(wrapper.findAllComponents(FormNumber).length).toBe(2);

        await wrapper.setProps({ value: 1, attributes: { multiple: false } });
        expect(wrapper.findComponent(FormNumberList).exists()).toBe(false);
        expect(wrapper.findAllComponents(FormNumber).length).toBe(1);
    });

    it("marks required values", async () => {
        const wrapper = mountElement();
        await wrapper.setProps({ type: "text", attributes: { optional: false } });
        expect(wrapper.find(".ui-form-title-star").exists()).toBe(true);
        expect(wrapper.find(".ui-form-title-message").exists()).toBe(false);
    });

    it("marks optional values", async () => {
        const wrapper = mountElement();
        await wrapper.setProps({ type: "text", attributes: { optional: true } });
        expect(wrapper.find(".ui-form-title-star").exists()).toBe(false);
        expect(wrapper.find(".ui-form-title-message").text()).toContain("optional");
    });

    it("warns about empty required values", async () => {
        const wrapper = mountElement();
        await wrapper.setProps({ type: "text", value: "", attributes: { optional: false } });
        expect(wrapper.find(".ui-form-title-star").exists()).toBe(true);
        expect(wrapper.find(".ui-form-title-message").text()).toContain("required");
    });

    it("renders html help through v-sanitize-html", async () => {
        const wrapper = mountElement();
        vi.mocked(sanitizeHtml).mockClear();
        await wrapper.setProps({ help: "Use <b>bold</b> values" });
        expect(sanitizeHtml).toHaveBeenLastCalledWith("Use <b>bold</b> values", "default");
        expect(wrapper.find(".ui-form-info b").text()).toBe("bold");
    });
});
