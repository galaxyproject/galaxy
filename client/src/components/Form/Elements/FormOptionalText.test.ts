import { getLocalVue } from "@tests/jest/helpers";
import { mount } from "@vue/test-utils";

import FormOptionalText from "./FormOptionalText.vue";

const localVue = getLocalVue();

async function mountFormOptionalText(propsData: object) {
    return mount(FormOptionalText as object, {
        localVue,
        propsData,
    });
}

describe("FormOptionalText", () => {
    it("should display existing values", async () => {
        const v = "some_value";
        const wrapper = await mountFormOptionalText({ value: v });

        const el = wrapper.find("input");
        expect((el.element as HTMLInputElement).checked).toEqual(true);

        const elText = wrapper.find("input[type='text']");
        expect((elText.element as HTMLInputElement).value).toEqual(v);

        await el.setChecked(false);

        expect(wrapper.emitted().input?.[0]?.[0]).toEqual(null);

        await el.setChecked(true);

        expect(wrapper.emitted().input?.[1]?.[0]).toEqual("");
    });

    it("should initialize with null if value does not exist", async () => {
        const wrapper = await mountFormOptionalText({ value: null });

        const el = wrapper.find("input");
        expect((el.element as HTMLInputElement).checked).toEqual(false);

        await wrapper.setProps({ value: "" });

        expect((el.element as HTMLInputElement).checked).toEqual(true);
    });
});
