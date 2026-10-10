import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import FormNumber from "./FormNumber.vue";
import FormText from "./FormText.vue";
import FormValueList from "./FormValueList.vue";

const localVue = getLocalVue();

function mountList(value: unknown, type = "integer", extraProps = {}) {
    return mount(FormValueList as object, {
        propsData: { value, type, ...extraProps },
        localVue,
    });
}

describe("FormValueList", () => {
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

    it("renders a text field per text value", () => {
        const wrapper = mountList(["a", "b"], "text");
        expect(wrapper.findAllComponents(FormText).length).toBe(2);
        expect(wrapper.findAllComponents(FormNumber).length).toBe(0);
    });

    it("keeps commas in a text value", () => {
        const wrapper = mountList("a,b", "text");
        const inputs = wrapper.findAll("input.ui-input");
        expect(inputs.length).toBe(1);
        expect((inputs.at(0)!.element as HTMLInputElement).value).toBe("a,b");
    });

    it("emits the entered text values as strings", async () => {
        const wrapper = mountList("a", "text");
        await wrapper.find("[data-description='add value']").trigger("click");
        await wrapper.findAll("input.ui-input").at(1)!.setValue("2");
        expect(wrapper.emitted("input")!.at(-1)).toEqual([["a", "2"]]);
    });

    it("offers text suggestions on every row", () => {
        const datalist = [
            { label: "First", value: "a" },
            { label: "Second", value: "b" },
        ];
        const wrapper = mountList(["a", "b"], "text", { id: "field", datalist });
        const inputs = wrapper.findAll("input.ui-input");
        const listIds = [inputs.at(0)!.attributes("list"), inputs.at(1)!.attributes("list")];
        expect(new Set(listIds).size).toBe(2);
        for (const listId of listIds) {
            const options = wrapper.findAll(`datalist[id='${listId}'] option`);
            expect(options.length).toBe(2);
            expect(options.at(0)!.attributes("value")).toBe("a");
            expect(options.at(1)!.attributes("value")).toBe("b");
        }
    });
});
