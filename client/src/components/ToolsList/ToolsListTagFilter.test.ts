import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import ToolsListTagFilter from "./ToolsListTagFilter.vue";

const localVue = getLocalVue();

function mountFilter(selectedTags: string[] = [], disabled = false) {
    return mount(ToolsListTagFilter, {
        localVue,
        pinia: createTestingPinia({ createSpy: vi.fn }),
        props: {
            tags: Array.from({ length: 1000 }, (_, index) => `Category ${index}`),
            selectedTags,
            disabled,
        },
    });
}

describe("ToolsListTagFilter", () => {
    it("reuses the ontology dropdown style, bounds rendered options, and searches all tags", async () => {
        const wrapper = mountFilter();
        const toggle = wrapper.get("button.dropdown-toggle");
        expect(toggle.classes()).toContain("btn-link");
        expect(toggle.classes()).toContain("btn-sm");
        await toggle.trigger("click");
        expect(wrapper.findAll("a.dropdown-item")).toHaveLength(100);
        const input = wrapper.get("input");
        expect(input.attributes("aria-label")).toBe("Search tags/categories");
        await input.setValue("category 999");
        expect(wrapper.findAll("a.dropdown-item")).toHaveLength(1);
        await wrapper.get("a.dropdown-item").trigger("click");
        expect(wrapper.emitted("toggle-tag")).toEqual([["Category 999"]]);
    });

    it("reflects external selection changes and allows removing selected tags", async () => {
        const wrapper = mountFilter(["data cleanup"]);
        expect(wrapper.get('button[title="Remove tag data cleanup"]').text()).toContain("data cleanup");
        await wrapper.get("button.dropdown-toggle").trigger("click");
        expect(wrapper.text()).not.toContain("Selected tags (click to remove)");
        await wrapper.get('button[title="Remove tag data cleanup"]').trigger("click");
        expect(wrapper.emitted("toggle-tag")).toEqual([["data cleanup"]]);
        await wrapper.setProps({ selectedTags: ["Category 500"] });
        expect(wrapper.get('button[title="Remove tag Category 500"]').text()).toContain("Category 500");
        await wrapper.get("input").setValue("Category 500");
        expect(wrapper.findAll("a.dropdown-item").filter((item) => item.text() === "Category 500")).toHaveLength(0);
    });

    it("treats selected tags case-insensitively, as the tag search does", async () => {
        const wrapper = mount(ToolsListTagFilter, {
            localVue,
            pinia: createTestingPinia({ createSpy: vi.fn }),
            props: { tags: ["Quality Control", "Get Data"], selectedTags: ["quality control"] },
        });
        await wrapper.get("button.dropdown-toggle").trigger("click");
        expect(wrapper.findAll("a.dropdown-item").map((item) => item.text())).toEqual(["Get Data"]);
    });

    it("removes a selected tag with its visible remove button without opening the menu", async () => {
        const wrapper = mountFilter(["data cleanup", "Category 500"]);
        const remove = wrapper.get('button[title="Remove tag data cleanup"]');
        expect(remove.find("svg").exists()).toBe(true);
        await remove.trigger("click");
        expect(wrapper.emitted("toggle-tag")).toEqual([["data cleanup"]]);
        expect(wrapper.get("button.dropdown-toggle").attributes("aria-expanded")).toBe("false");
    });

    it("shows loading feedback instead of an empty catalog while fetching tags", async () => {
        const wrapper = mountFilter();
        await wrapper.setProps({ tags: [], loading: true });
        await wrapper.get("button.dropdown-toggle").trigger("click");
        expect(wrapper.text()).toContain("Loading tags/categories...");
        expect(wrapper.text()).not.toContain("No tags available.");
        expect(wrapper.get("input").attributes("placeholder")).toBe("Search tags/categories");
    });

    it("shows empty search feedback and respects disabled state", async () => {
        const wrapper = mountFilter();
        await wrapper.get("button.dropdown-toggle").trigger("click");
        await wrapper.get("input").setValue("no such category");
        expect(wrapper.text()).toContain("No matching tags found.");
        await wrapper.setProps({ disabled: true });
        expect(wrapper.get("button.dropdown-toggle").attributes("disabled")).toBeDefined();
    });
});
