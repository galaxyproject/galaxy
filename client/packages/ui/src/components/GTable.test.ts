import "@testing-library/jest-dom/vitest";

import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import GTable from "./GTable.vue";

enableAutoUnmount(afterEach);

const items = [
    { id: 1, name: "first" },
    { id: 2, name: "second" },
];

function mountSelectable(props: Record<string, unknown> = {}) {
    return mount(GTable as object, {
        props: {
            items,
            fields: [{ key: "name" }],
            selectable: true,
            clickableRows: true,
            showSelectAll: true,
            ...props,
        },
        attachTo: document.body,
    });
}

function checkbox(element: Element | undefined) {
    return element as HTMLInputElement;
}

describe("GTable selection", () => {
    it.each([undefined, "Select dataset"])("names the selection checkboxes (%s)", (title) => {
        const wrapper = mount(GTable as object, {
            props: {
                items,
                fields: [{ key: "name" }],
                selectable: true,
                showSelectAll: true,
                selectCheckboxTitle: title,
            },
            attachTo: document.body,
        });

        expect(wrapper.get("thead input").element).toHaveAccessibleName("Select all for bulk actions");
        for (const checkbox of wrapper.findAll("tbody input")) {
            expect(checkbox.element).toHaveAccessibleName(title ?? "Select for bulk actions");
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

    it("selects all from the header checkbox", async () => {
        const wrapper = mountSelectable();

        await wrapper.get("thead .g-checkbox").trigger("click");

        expect(wrapper.emitted("select-all")).toEqual([[true]]);
    });

    it("shows partial selection on the header and on indeterminate rows", () => {
        const wrapper = mountSelectable({ selectedItems: [0], indeterminateItems: [1] });
        const [first, second] = wrapper.findAll("tbody input").map((row) => checkbox(row.element));
        const header = checkbox(wrapper.get("thead input").element);

        expect(header.indeterminate).toBe(true);
        expect(first!.checked).toBe(true);
        expect(first!.indeterminate).toBe(false);
        expect(second!.indeterminate).toBe(true);
    });

    it("checks the header, not partially, once every row is selected", () => {
        const wrapper = mountSelectable({ selectedItems: [0, 1] });
        const header = checkbox(wrapper.get("thead input").element);

        expect(header.checked).toBe(true);
        expect(header.indeterminate).toBe(false);
    });
});

describe("GTable sorting", () => {
    function mountSortable(slots: Record<string, string> = {}) {
        return mount(GTable as object, {
            props: {
                items,
                fields: [
                    { key: "name", label: "Name", sortable: true },
                    { key: "id", label: "Id", sortable: true },
                    { key: "note", label: "Note" },
                ],
                sortBy: "name",
            },
            slots,
            attachTo: document.body,
        });
    }

    it("exposes the sort state on sortable headers only", () => {
        const wrapper = mountSortable();
        const [name, id, note] = wrapper.findAll("thead th");

        expect(name!.attributes("aria-sort")).toBe("ascending");
        expect(name!.attributes("tabindex")).toBe("0");
        expect(id!.attributes("aria-sort")).toBe("none");
        expect(id!.attributes("tabindex")).toBe("0");
        expect(note!.attributes("aria-sort")).toBeUndefined();
        expect(note!.attributes("tabindex")).toBeUndefined();
    });

    it("sorts from the keyboard with Enter and Space", async () => {
        const wrapper = mountSortable();
        const name = wrapper.findAll("thead th")[0]!;

        await name.trigger("keydown", { key: "Enter" });
        expect(wrapper.emitted("sort-changed")).toEqual([["name", true]]);
        expect(name.attributes("aria-sort")).toBe("descending");
        expect(wrapper.findAll("tbody tr td:first-child").map((cell) => cell.text())).toEqual(["second", "first"]);

        await name.trigger("keydown", { key: " " });
        expect(wrapper.emitted("sort-changed")).toEqual([
            ["name", true],
            ["name", false],
        ]);
    });

    // Space would otherwise scroll the page as well as sorting
    it("keeps Space on a sortable header from scrolling the page", () => {
        const wrapper = mountSortable();
        const space = new KeyboardEvent("keydown", { key: " ", cancelable: true });

        wrapper.findAll("thead th")[0]!.element.dispatchEvent(space);

        expect(space.defaultPrevented).toBe(true);
    });

    it("leaves Enter alone for a control inside a header slot", async () => {
        const wrapper = mountSortable({ "head(name)": "<button class='head-control'>Options</button>" });

        await wrapper.get(".head-control").trigger("keydown", { key: "Enter" });

        expect(wrapper.emitted("sort-changed")).toBeUndefined();
    });
});
