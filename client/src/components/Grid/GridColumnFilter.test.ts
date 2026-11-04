import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import type { FieldFilter, FilterOption } from "./configs/types";

import GridColumnFilter from "./GridColumnFilter.vue";

vi.useFakeTimers();

const localVue = getLocalVue();

const RESULTS: FilterOption[] = [
    { id: "workflow-1", name: "RNA-seq", updateTime: "2026-11-01T10:00:00", detail: () => "2 runs" },
    { id: "workflow-2", name: "Variant calling" },
];

function mountFilter(selected: FilterOption[] = [], results = RESULTS) {
    const filter: FieldFilter = { key: "workflow_id", plural: "workflows", search: vi.fn(async () => results) };
    const wrapper = mount(GridColumnFilter as object, {
        props: { filter, title: "Workflow", selected },
        global: localVue,
        attachTo: document.body,
    });
    return { wrapper, filter };
}

async function open(wrapper: ReturnType<typeof mountFilter>["wrapper"]) {
    await wrapper.find("button").trigger("click");
    await flushPromises();
}

function optionNames(wrapper: ReturnType<typeof mountFilter>["wrapper"]) {
    return wrapper.findAll(".grid-column-filter-option").map((option) => option.find(".font-weight-bold").text());
}

describe("GridColumnFilter", () => {
    it("lists selected items first, checked, followed by the search results", async () => {
        const { wrapper } = mountFilter([{ id: "workflow-2", name: "Variant calling" }]);
        await open(wrapper);

        expect(optionNames(wrapper)).toEqual(["Variant calling", "RNA-seq"]);
        const checkboxes = wrapper.findAll<HTMLInputElement>(".grid-column-filter-option input");
        expect(checkboxes.map((checkbox) => checkbox.element.checked)).toEqual([true, false]);
        expect(wrapper.findAll(".grid-column-filter-option")[1]!.find("small").text()).toMatch(
            /^2 runs · updated .+ ago$/,
        );
        expect(wrapper.find("[data-description='grid column filter count']").text()).toBe("1");
    });

    it("searches as you type and emits the toggled selection", async () => {
        const { wrapper, filter } = mountFilter();
        await open(wrapper);
        expect(filter.search).toHaveBeenCalledWith("");

        await wrapper.find("[data-description='grid column filter search']").setValue(" rna ");
        vi.advanceTimersByTime(300);
        await flushPromises();
        expect(filter.search).toHaveBeenLastCalledWith("rna");

        await wrapper.find("input[data-description='grid column filter option workflow-1']").setValue(true);
        expect(wrapper.emitted("update:selected")).toEqual([[[RESULTS[0]]]]);
    });

    it("unchecks and clears selected items", async () => {
        const selected = [RESULTS[0]!, RESULTS[1]!];
        const { wrapper } = mountFilter(selected);
        await open(wrapper);

        await wrapper.find("input[data-description='grid column filter option workflow-1']").setValue(false);
        await wrapper.find("[data-description='grid column filter clear']").trigger("click");
        expect(wrapper.emitted("update:selected")).toEqual([[[RESULTS[1]]], [[]]]);
    });

    it("says when nothing matches", async () => {
        const { wrapper } = mountFilter([], []);
        await open(wrapper);
        await wrapper.find("[data-description='grid column filter search']").setValue("missing");
        vi.advanceTimersByTime(300);
        await flushPromises();

        expect(wrapper.find(".grid-column-filter-options").text()).toBe('No workflows match "missing"');
    });
});
