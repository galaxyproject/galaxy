import { emittedArg, getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import FormOptionalText from "./FormOptionalText.vue";

const localVue = getLocalVue();

describe("FormOptionalText", () => {
    const mountFormOptionalText = async (props) =>
        await mount(FormOptionalText, {
            props: props,
            global: localVue,
        });

    it("should display existing values", async () => {
        const v = "somevalue";
        const wrapper = await mountFormOptionalText({ value: v });
        const el = wrapper.find("input");
        expect(el.element.checked).toEqual(true);
        const elText = wrapper.find("input[type='text']");
        expect(elText.element.value).toEqual(v);
        await el.setValue(false);
        expect(emittedArg(wrapper, "input")).toEqual(null);
        await el.setValue(true);
        expect(emittedArg(wrapper, "input", 1)).toEqual("");
    });

    it("names an optional input and keeps its label associated after toggling", async () => {
        const wrapper = await mountFormOptionalText({ value: "hg38" });
        const label = wrapper.find("label.sr-only");
        expect(label.text()).toBe("Optional value");
        expect(label.attributes("for")).toBe(wrapper.find("input[type=text]").attributes("id"));
        await wrapper.find("input[type=checkbox]").setValue(false);
        await wrapper.setProps({ value: null });
        expect(wrapper.find("label.sr-only").exists()).toBe(false);
        await wrapper.find("input[type=checkbox]").setValue(true);
        await wrapper.setProps({ value: "" });
        expect(wrapper.find("label.sr-only").attributes("for")).toBe(label.attributes("for"));
    });

    it("renders the optional toggle as a switch on the ui-switch label", async () => {
        const wrapper = await mountFormOptionalText({ value: null });
        const toggle = wrapper.find("label.ui-switch");
        expect(toggle.text()).toBe("Set value for this optional select field?");
        expect(toggle.find("input[type=checkbox]").attributes("role")).toBe("switch");
    });

    it("should initialize with null if value does not exist", async () => {
        const v = null;
        const wrapper = await mountFormOptionalText({ value: v });
        const el = wrapper.find("input");
        expect(el.element.checked).toEqual(false);
        await wrapper.setProps({ value: "" });
        expect(el.element.checked).toEqual(true);
    });
});
