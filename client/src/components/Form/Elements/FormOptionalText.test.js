import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import FormOptionalText from "./FormOptionalText";

const globalConfig = getLocalVue();

describe("FormOptionalText", () => {
    const mountFormOptionalText = async (props) =>
        await mount(FormOptionalText, {
            props,
            global: globalConfig.global,
        });

    it("should display existing values", async () => {
        const v = "somevalue";
        const wrapper = await mountFormOptionalText({ value: v });
        const el = wrapper.find("input[type='checkbox']");
        expect(el.element.checked).toEqual(true);
        const elText = wrapper.find("input[type='text']");
        expect(elText.element.value).toEqual(v);
        // TODO: Fix form interactions with setChecked in Vue 3
        // await el.setChecked(false);
        // expect(wrapper.emitted().input[0][0]).toEqual(null);
        // await el.setChecked(true);
        // expect(wrapper.emitted().input[1][0]).toEqual("");
    });

    it("should initialize with null if value does not exist", async () => {
        const v = null;
        const wrapper = await mountFormOptionalText({ value: v });
        // When value is null, renders as b-form-checkbox component
        const el = wrapper.find("b-form-checkbox");
        expect(el.exists()).toBe(true);
        expect(el.attributes("modelvalue")).toBeFalsy();
        
        await wrapper.setProps({ value: "" });
        // After setting empty string, should become checked (stays as b-form-checkbox)
        const elAfter = wrapper.find("b-form-checkbox");
        expect(elAfter.exists()).toBe(true);
        expect(elAfter.attributes("modelvalue")).toBe("true");
    });
});
