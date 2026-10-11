import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import FormNumber from "./FormNumber.vue";
import FormNumberList from "./FormNumberList.vue";

const localVue = getLocalVue();

function mountList(value: unknown) {
    return mount(FormNumberList as object, {
        propsData: { value, type: "integer" },
        localVue,
    });
}

describe("FormNumberList", () => {
    it("renders a number field per value", () => {
        const wrapper = mountList([1, 2]);
        const inputs = wrapper.findAll("input.ui-input");
        expect(inputs.length).toBe(2);
        expect((inputs.at(0)!.element as HTMLInputElement).value).toBe("1");
        expect((inputs.at(1)!.element as HTMLInputElement).value).toBe("2");
    });

    it("starts with one empty field", () => {
        const wrapper = mountList(null);
        expect(wrapper.findAllComponents(FormNumber).length).toBe(1);
        expect(wrapper.find("[data-description='remove value']").classes()).toContain("g-disabled");
    });

    it("emits the entered values as numbers", async () => {
        const wrapper = mountList([1]);
        await wrapper.find("[data-description='add value']").trigger("click");
        await wrapper.findAll("input.ui-input").at(1)!.setValue("3");
        expect(wrapper.emitted("input")!.at(-1)).toEqual([[1, 3]]);
    });

    it("removes a value", async () => {
        const wrapper = mountList([1, 2]);
        await wrapper.findAll("[data-description='remove value']").at(0)!.trigger("click");
        expect(wrapper.emitted("input")!.at(-1)).toEqual([[2]]);
        expect(wrapper.findAllComponents(FormNumber).length).toBe(1);
    });

    it("emits null once every field is empty", async () => {
        const wrapper = mountList([1]);
        await wrapper.find("input.ui-input").setValue("");
        expect(wrapper.emitted("input")!.at(-1)).toEqual([null]);
    });
});
