import { emittedArg, getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import FormOptionalText from "./FormOptionalText.vue";

const localVue = getLocalVue();

const SELECTORS = {
    SWITCH: "input[type='checkbox']",
    TEXT_INPUT: "input[type='text']",
};

function mountFormOptionalText(value) {
    return mount(FormOptionalText, {
        props: { value },
        global: localVue,
    });
}

describe("FormOptionalText", () => {
    it("switches on and shows an existing value", () => {
        const wrapper = mountFormOptionalText("somevalue");

        expect(wrapper.find(SELECTORS.SWITCH).element.checked).toBe(true);
        expect(wrapper.find(SELECTORS.TEXT_INPUT).element.value).toBe("somevalue");
    });

    it("emits null when switched off and an empty string when switched back on", async () => {
        const wrapper = mountFormOptionalText("somevalue");
        const toggle = wrapper.find(SELECTORS.SWITCH);

        await toggle.setValue(false);
        expect(emittedArg(wrapper, "input", 0)).toBeNull();

        await toggle.setValue(true);
        expect(emittedArg(wrapper, "input", 1)).toBe("");
    });

    it("starts switched off for a null value and switches on once a value is set", async () => {
        const wrapper = mountFormOptionalText(null);
        const toggle = wrapper.find(SELECTORS.SWITCH);
        expect(toggle.element.checked).toBe(false);
        expect(wrapper.find(SELECTORS.TEXT_INPUT).exists()).toBe(false);

        await wrapper.setProps({ value: "" });

        expect(toggle.element.checked).toBe(true);
        expect(wrapper.find(SELECTORS.TEXT_INPUT).exists()).toBe(true);
    });
});
