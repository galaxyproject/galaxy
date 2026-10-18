import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import type { SelectionItem, SelectItemsQuery } from "./selectionTypes";

import DataDialogSearch from "./DataDialogSearch.vue";
import SelectionPanel from "./SelectionPanel.vue";

interface Raw {
    id: string;
    name: string;
}

function toItem(raw: Raw): SelectionItem {
    return { id: raw.id, label: raw.name, details: "", isLeaf: raw.id !== "folder", url: "", entry: { ...raw } };
}

/** Returns a whole level at once, so the panel pages and searches locally. */
function clientProvider() {
    const root = [
        { id: "folder", name: "folder" },
        ...Array.from({ length: 29 }, (_, i) => ({ id: `${i}`, name: `file ${i}` })),
    ];
    const load = vi.fn(async (query: SelectItemsQuery) => ({
        items: query.path.length ? [{ id: "inner", name: "inner file" }] : root,
    }));
    return { provider: { load, map: toItem }, load };
}

function rowLabels(wrapper: ReturnType<typeof mount>) {
    return wrapper.findAll("td[id^='g-table-cell-label-']").map((cell) => cell.text());
}

describe("SelectionPanel.vue", () => {
    it("renders a level without a modal and pages it locally", async () => {
        const { provider, load } = clientProvider();
        const wrapper = mount(SelectionPanel as object, { props: { provider }, global: getLocalVue() });
        await flushPromises();
        expect(wrapper.find(".selection-dialog-modal").exists()).toBe(false);
        expect(rowLabels(wrapper)).toHaveLength(25);

        await wrapper.find("[aria-label='Go to page 2']").trigger("click");
        expect(rowLabels(wrapper)).toEqual(["file 24", "file 25", "file 26", "file 27", "file 28"]);
        expect(load).toHaveBeenCalledTimes(1);
    });

    it("searches the loaded level", async () => {
        const { provider, load } = clientProvider();
        const wrapper = mount(SelectionPanel as object, { props: { provider }, global: getLocalVue() });
        await flushPromises();

        wrapper.findComponent(DataDialogSearch).vm.$emit("input", "file 2");
        await flushPromises();
        expect(rowLabels(wrapper)).toEqual([
            "file 2",
            "file 20",
            "file 21",
            "file 22",
            "file 23",
            "file 24",
            "file 25",
            "file 26",
            "file 27",
            "file 28",
        ]);
        expect(wrapper.find("[aria-label='Go to page 2']").exists()).toBe(false);
        expect(load).toHaveBeenCalledTimes(1);
    });

    it("opens a folder and goes back", async () => {
        const { provider } = clientProvider();
        const wrapper = mount(SelectionPanel as object, { props: { provider }, global: getLocalVue() });
        await flushPromises();

        await wrapper.get("button.selection-dialog-folder").trigger("click");
        await flushPromises();
        expect(rowLabels(wrapper)).toEqual(["inner file"]);

        await wrapper.get("[data-description='selection panel back']").trigger("click");
        await flushPromises();
        expect(rowLabels(wrapper)).toHaveLength(25);
        expect(wrapper.emitted("back")).toHaveLength(1);
    });

    it("renders an empty list and warns without a provider or state", async () => {
        const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
        const wrapper = mount(SelectionPanel as object, { global: getLocalVue() });
        await flushPromises();
        expect(rowLabels(wrapper)).toEqual([]);
        expect(warn).toHaveBeenCalledWith(expect.stringContaining("SelectionPanel needs a provider or state"));
        warn.mockRestore();
    });
});
