import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import GTable from "./GTable.vue";

const items = [
    { id: 1, name: "first" },
    { id: 2, name: "second" },
];

function mountSelectable() {
    return mount(GTable as object, {
        props: { items, fields: [{ key: "name" }], selectable: true, clickableRows: true, showSelectAll: true },
        attachTo: document.body,
    });
}

describe("GTable selection", () => {
    // Selenium clicks the checkbox's label; the click must stop at the checkbox rather than
    // also reaching the row, whose own handler would toggle the selection a second time.
    it("selects a row once from its checkbox without counting a row click", async () => {
        const wrapper = mountSelectable();

        await wrapper.findAll("tbody tr")[0]!.get(".g-checkbox").trigger("click");

        expect(wrapper.emitted("row-select")).toEqual([[{ item: items[0], index: 0, selected: true }]]);
        expect(wrapper.emitted("row-click")).toBeUndefined();
    });

    it("selects all once from the header checkbox", async () => {
        const wrapper = mountSelectable();

        await wrapper.get("thead .g-checkbox").trigger("click");

        expect(wrapper.emitted("select-all")).toEqual([[true]]);
    });
});
