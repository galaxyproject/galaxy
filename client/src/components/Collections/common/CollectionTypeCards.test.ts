import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import CollectionTypeCards from "./CollectionTypeCards.vue";

const localVue = getLocalVue();

function mountWithValue(value?: string) {
    return mount(CollectionTypeCards as object, { propsData: { value, context: "workflow_input" }, localVue });
}

function cardTitles(wrapper: VueWrapper) {
    return wrapper.findAll("[data-collection-type] .card-title").map((title) => title.text());
}

describe("CollectionTypeCards", () => {
    it.each(["click", "keydown.enter", "keydown.space"])("picks a collection type on %s", async (event) => {
        const wrapper = mountWithValue();
        await wrapper.find("[data-collection-type='list:paired']").trigger(event);
        expect(wrapper.emitted("select")).toEqual([["list:paired"]]);
    });

    it("shows every known collection type under its group", () => {
        const wrapper = mountWithValue();
        expect(wrapper.findAll("h3").map((heading) => heading.text())).toEqual([
            "Lists",
            "Pairs and Records",
            "Nested Lists",
            "Sample Sheets",
        ]);
        expect(wrapper.findAll("[data-collection-type]")).toHaveLength(12);
        expect(wrapper.find("[data-collection-type='list:paired'] code").text()).toBe("list:paired");
    });

    it("shows only the collection types asked for, in order and ungrouped", () => {
        const wrapper = mount(CollectionTypeCards as object, {
            propsData: { types: ["list:list", "list"], context: "builder", hideType: true },
            slots: { extra: "<div class='extra-card'>Rule Builder</div>" },
            localVue,
        });
        expect(cardTitles(wrapper)).toEqual(["Nested List of Datasets", "Flat List"]);
        expect(wrapper.find("h3").exists()).toBe(false);
        expect(wrapper.find("code").exists()).toBe(false);
        expect(wrapper.find(".collection-type-card-grid .extra-card").text()).toBe("Rule Builder");
    });

    it("describes each collection type for where it's being chosen", () => {
        const connectable = "can also be connected to this input";
        const forWorkflowInput = mountWithValue();
        expect(forWorkflowInput.find("[data-collection-type='list:paired_or_unpaired']").text()).toContain(connectable);
        const forBuilder = mount(CollectionTypeCards as object, {
            propsData: { types: ["list:paired", "list:paired_or_unpaired"], context: "builder" },
            localVue,
        });
        expect(forBuilder.find("[data-collection-type='list:paired_or_unpaired']").text()).not.toContain(connectable);
        expect(forBuilder.find("[data-collection-type='list:paired']").text()).toContain(
            "Use this option if all of your data should be paired off.",
        );
    });

    it("marks the current collection type", () => {
        const wrapper = mountWithValue("sample_sheet");
        expect(wrapper.find("[data-collection-type='sample_sheet']").classes()).toContain("border-primary");
        expect(wrapper.find("[data-collection-type='list']").classes()).not.toContain("border-primary");
    });
});
