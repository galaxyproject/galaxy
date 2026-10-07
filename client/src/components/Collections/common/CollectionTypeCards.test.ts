import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import CollectionTypeCards from "./CollectionTypeCards.vue";

const localVue = getLocalVue();

function mountWithValue(value?: string) {
    return mount(CollectionTypeCards as object, { propsData: { value }, localVue });
}

describe("CollectionTypeCards", () => {
    it.each(["click", "keydown.enter", "keydown.space"])("picks a collection type on %s", async (event) => {
        const wrapper = mountWithValue();
        await wrapper.find("[data-collection-type='list:paired']").trigger(event);
        expect(wrapper.emitted("select")).toEqual([["list:paired"]]);
    });

    it("marks the current collection type", () => {
        const wrapper = mountWithValue("sample_sheet");
        expect(wrapper.find("[data-collection-type='sample_sheet']").classes()).toContain("border-primary");
        expect(wrapper.find("[data-collection-type='list']").classes()).not.toContain("border-primary");
    });
});
