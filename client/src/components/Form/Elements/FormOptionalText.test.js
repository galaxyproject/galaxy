import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import FormOptionalText from "./FormOptionalText";

const localVue = getLocalVue();

describe("FormOptionalText", () => {
    const mountFormOptionalText = async (props) =>
        await mount(FormOptionalText, {
            propsData: props,
            localVue,
        });

    it("should display existing values", async () => {
        const v = "somevalue";
        const wrapper = await mountFormOptionalText({ value: v });
        const el = wrapper.find("input");
        expect(el.element.checked).toEqual(true);
        const elText = wrapper.find("input[type='text']");
        expect(elText.element.value).toEqual(v);
        await el.setChecked(false);
        expect(wrapper.emitted().input[0][0]).toEqual(null);
        await el.setChecked(true);
        expect(wrapper.emitted().input[1][0]).toEqual("");
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
