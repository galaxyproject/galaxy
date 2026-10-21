import "@testing-library/jest-dom/vitest";

import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, onTestFinished } from "vitest";

import * as GTableStories from "@/components/Common/GTable.stories";

import GTable from "./GTable.vue";

const stories = composeStories(GTableStories);
const mountStory = useStoryMount();

enableAutoUnmount(afterEach);

const items = [
    { id: 1, name: "first" },
    { id: 2, name: "second" },
];

type TableProps = Parameters<typeof GTable>[0];

function attachmentTarget() {
    const target = document.createElement("div");
    document.body.appendChild(target);
    onTestFinished(() => target.remove());
    return target;
}

function mountSelectable(props: TableProps = {}) {
    const wrapper = mountStory(stories.SelectableDatasets, {
        props: { items, fields: [{ key: "name" }], ...props },
        attachTo: attachmentTarget(),
    });
    return wrapper.getComponent(GTable);
}

describe("GTable selection", () => {
    // Selenium clicks the checkbox's label; the click must stop at the checkbox rather than
    // also reaching the row, whose own handler would toggle the selection a second time.
    it("selects a row once from its checkbox without counting a row click", async () => {
        const wrapper = mountSelectable();
        expect(wrapper.get<HTMLInputElement>("tbody input").element.checked).toBe(false);

        await wrapper.get("tbody tr").get(".g-checkbox").trigger("click");

        expect(wrapper.emitted("row-select")).toEqual([[{ item: items[0], index: 0, selected: true }]]);
        expect(wrapper.emitted("row-click")).toBeUndefined();
    });

    it("selects all from the header checkbox", async () => {
        const wrapper = mountSelectable();
        expect(wrapper.get<HTMLInputElement>("thead input").element.checked).toBe(false);

        await wrapper.get("thead .g-checkbox").trigger("click");

        expect(wrapper.emitted("select-all")).toEqual([[true]]);
    });

    it("shows partial selection on the header and on indeterminate rows", () => {
        const wrapper = mountSelectable({ selectedItems: [0], indeterminateItems: [1] });
        const first = wrapper.get<HTMLInputElement>("tbody tr:first-child input").element;
        const second = wrapper.get<HTMLInputElement>("tbody tr:nth-child(2) input").element;
        const header = wrapper.get<HTMLInputElement>("thead input").element;

        expect(header.indeterminate).toBe(true);
        expect(first.checked).toBe(true);
        expect(first.indeterminate).toBe(false);
        expect(second.indeterminate).toBe(true);
    });

    it("checks the header, not partially, once every row is selected", () => {
        const wrapper = mountSelectable({ selectedItems: [0, 1] });
        const header = wrapper.get<HTMLInputElement>("thead input").element;

        expect(header.checked).toBe(true);
        expect(header.indeterminate).toBe(false);
    });
});

describe("GTable sorting", () => {
    function mountSortable(slots: Record<string, string> = {}) {
        const props = { ...GTableStories.SortableDatasets.args, items };
        if (Object.keys(slots).length) {
            // A nested header control is a test-only slot; retain its direct native keyboard contract.
            return mount(GTable, { props, slots, attachTo: attachmentTarget() });
        }
        const wrapper = mountStory(stories.SortableDatasets, { props, attachTo: attachmentTarget() });
        return wrapper.getComponent(GTable);
    }

    it("exposes the sort state on sortable headers only", () => {
        const wrapper = mountSortable();
        const name = wrapper.get("thead th:first-child");
        const id = wrapper.get("thead th:nth-child(2)");
        const note = wrapper.get("thead th:nth-child(3)");

        expect(name.attributes("aria-sort")).toBe("ascending");
        expect(name.attributes("tabindex")).toBe("0");
        expect(id.attributes("aria-sort")).toBe("none");
        expect(id.attributes("tabindex")).toBe("0");
        expect(note.attributes("aria-sort")).toBeUndefined();
        expect(note.attributes("tabindex")).toBeUndefined();
    });

    it("sorts from the keyboard with Enter and Space", async () => {
        const wrapper = mountSortable();
        const name = wrapper.get("thead th");

        expect(name.attributes("aria-sort")).toBe("ascending");
        expect(wrapper.findAll("tbody tr td:first-child").map((cell) => cell.text())).toEqual(["first", "second"]);

        await name.trigger("keydown", { key: "Enter" });
        expect(wrapper.emitted("sort-changed")).toEqual([["name", true]]);

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

        wrapper.get("thead th").element.dispatchEvent(space);

        expect(space.defaultPrevented).toBe(true);
    });

    it("leaves Enter alone for a control inside a header slot", async () => {
        const wrapper = mountSortable({ "head(name)": "<button class='head-control'>Options</button>" });

        await wrapper.get(".head-control").trigger("keydown", { key: "Enter" });

        expect(wrapper.emitted("sort-changed")).toBeUndefined();
    });
});
