import { enableAutoUnmount, mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import RuleGrid from "./RuleGrid.vue";

const DATA = [
    ["1", "a.bed"],
    ["2", "b.bed"],
];
const COL_HEADERS = ["A", "B"];

enableAutoUnmount(afterEach);

async function mountRuleGrid(highlightedColumns: number[]) {
    const wrapper = mount(RuleGrid, {
        props: { data: DATA, colHeaders: COL_HEADERS, highlightedColumns },
        attachTo: document.body,
    });
    // AG Grid loads asynchronously and renders its rows after that.
    await vi.waitFor(() => expect(wrapper.findAll(".ag-cell")).toHaveLength(4), { timeout: 5000 });
    return wrapper;
}

function highlightedText(wrapper: VueWrapper, selector: string) {
    return wrapper
        .findAll(selector)
        .filter((element) => element.classes().includes("rule-highlight"))
        .map((element) => element.text());
}

describe("RuleGrid", () => {
    it("highlights the header and cells of the highlighted columns", async () => {
        const wrapper = await mountRuleGrid([1]);

        expect(highlightedText(wrapper, ".ag-header-cell")).toEqual(["B"]);
        expect(highlightedText(wrapper, ".ag-cell")).toEqual(["a.bed", "b.bed"]);
    });

    it("moves the highlight when the highlighted columns change", async () => {
        const wrapper = await mountRuleGrid([]);
        // The first change may land before the grid is ready; once it shows, the grid is.
        await wrapper.setProps({ highlightedColumns: [1] });
        await vi.waitFor(() => expect(highlightedText(wrapper, ".ag-header-cell")).toEqual(["B"]));

        await wrapper.setProps({ highlightedColumns: [0] });

        await vi.waitFor(() => expect(highlightedText(wrapper, ".ag-header-cell")).toEqual(["A"]));
        expect(highlightedText(wrapper, ".ag-cell")).toEqual(["1", "2"]);
    });

    it("removes the highlight when the highlighted columns are cleared", async () => {
        const wrapper = await mountRuleGrid([]);
        await wrapper.setProps({ highlightedColumns: [1] });
        await vi.waitFor(() => expect(highlightedText(wrapper, ".ag-cell")).toEqual(["a.bed", "b.bed"]));

        await wrapper.setProps({ highlightedColumns: [] });

        await vi.waitFor(() => expect(highlightedText(wrapper, ".ag-header-cell")).toEqual([]));
        expect(highlightedText(wrapper, ".ag-cell")).toEqual([]);
    });
});
