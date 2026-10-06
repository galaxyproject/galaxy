import "@testing-library/jest-dom/vitest";

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
    it.each([undefined, "Select dataset"])("names selection checkboxes without the tooltip directive (%s)", (title) => {
        const wrapper = mount(GTable as object, {
            props: {
                items,
                fields: [{ key: "name" }],
                selectable: true,
                showSelectAll: true,
                selectCheckboxTitle: title,
            },
            global: { directives: { "g-tooltip": {} } },
            attachTo: document.body,
        });

        try {
            expect(wrapper.get("thead input").element).toHaveAccessibleName("Select all for bulk actions");
            for (const checkbox of wrapper.findAll("tbody input")) {
                expect(checkbox.element).toHaveAccessibleName(title ?? "Select for bulk actions");
            }
        } finally {
            wrapper.unmount();
        }
    });

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

describe("GTable sorting", () => {
    function mountSortable() {
        return mount(GTable as object, {
            props: {
                items,
                fields: [
                    { key: "name", label: "Name", sortable: true },
                    { key: "id", label: "Id" },
                ],
                sortBy: "name",
            },
            attachTo: document.body,
        });
    }

    it("exposes the sort state on sortable headers only", () => {
        const wrapper = mountSortable();
        const [name, id] = wrapper.findAll("thead th");

        expect(name!.attributes("aria-sort")).toBe("ascending");
        expect(name!.attributes("tabindex")).toBe("0");
        expect(id!.attributes("aria-sort")).toBeUndefined();
        expect(id!.attributes("tabindex")).toBeUndefined();
    });

    it("sorts from the keyboard with Enter and Space", async () => {
        const wrapper = mountSortable();
        const name = wrapper.findAll("thead th")[0]!;

        await name.trigger("keydown", { key: "Enter" });
        expect(wrapper.emitted("sort-changed")).toEqual([["name", true]]);
        expect(name.attributes("aria-sort")).toBe("descending");

        await name.trigger("keydown", { key: " " });
        expect(wrapper.emitted("sort-changed")).toEqual([
            ["name", true],
            ["name", false],
        ]);
    });
});
