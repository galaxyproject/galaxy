import { emittedArg, getLocalVue, nth } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";

import { SELECTION_STATES } from "./selectionTypes";

import DataDialogSearch from "./DataDialogSearch.vue";
import SelectionDialog from "./SelectionDialog.vue";
import GTable from "@/components/Common/GTable.vue";

const mockOptions = {
    callback: () => {},
    modalShow: true,
};

describe("SelectionDialog.vue", () => {
    let wrapper;
    let localVue;

    beforeEach(() => {
        localVue = getLocalVue();
        wrapper = mount(SelectionDialog, {
            props: mockOptions,
            global: localVue,
        });
    });

    it("loads correctly in loading state, shows options when optionsShow becomes true", async () => {
        expect(wrapper.find("[data-description='selection dialog spinner']").exists()).toBeTruthy();
        expect(wrapper.findComponent(GTable).exists()).toBeFalsy();
        await wrapper.setProps({ optionsShow: true });
        expect(wrapper.find("[data-description='selection dialog spinner']").exists()).toBeFalsy();
        expect(wrapper.findComponent(GTable).exists()).toBeTruthy();
    });

    it("opens a folder without also selecting its row", async () => {
        const folder = { id: "folder", label: "Results", url: "gxfiles://results", isLeaf: false };
        await wrapper.setProps({ optionsShow: true, selectable: true, items: [folder] });
        const open = wrapper.get("button.selection-dialog-folder");
        expect(open.text()).toContain("Results");
        expect(open.find("a").exists()).toBe(false);
        await open.trigger("click");
        expect(wrapper.emitted("onOpen")).toEqual([[folder]]);
        expect(wrapper.emitted("onClick")).toBeUndefined();
    });

    it("names the search and its clear button", () => {
        expect(wrapper.get("input[type='text']").attributes("aria-label")).toContain("search");
        expect(wrapper.get("button[aria-label='Clear search']").exists()).toBe(true);
    });

    it("loads header correctly", async () => {
        await nextTick();
        expect(wrapper.findComponent(DataDialogSearch).exists()).toBeTruthy();
    });

    it("hideModal called on click cancel", async () => {
        expect(wrapper.emitted("onCancel")).toBeFalsy();
        wrapper.find("[data-description='selection dialog cancel']").trigger("click");
        expect(wrapper.emitted("onCancel")).toBeTruthy();
    });

    it("syncs row selection state from incoming items", async () => {
        await wrapper.setProps({
            optionsShow: true,
            selectable: true,
            items: [
                { id: "1", label: "file1", isLeaf: true, selectionState: SELECTION_STATES.SELECTED },
                { id: "2", label: "file2", isLeaf: true, selectionState: SELECTION_STATES.UNSELECTED },
            ],
        });

        const selectAllCheckbox = wrapper.find("input[id^='g-table-select-all-']").element;
        expect(selectAllCheckbox.checked).toBe(false);
        expect(selectAllCheckbox.indeterminate).toBe(true);
    });

    it("shows select-all as checked when all incoming items are selected", async () => {
        await wrapper.setProps({
            optionsShow: true,
            selectable: true,
            items: [
                { id: "1", label: "file1", isLeaf: true, selectionState: SELECTION_STATES.SELECTED },
                { id: "2", label: "file2", isLeaf: true, selectionState: SELECTION_STATES.SELECTED },
            ],
        });

        const selectAllCheckbox = wrapper.find("input[id^='g-table-select-all-']").element;
        expect(selectAllCheckbox.checked).toBe(true);
        expect(selectAllCheckbox.indeterminate).toBe(false);
    });

    it("renders a MIXED row as an indeterminate checkbox", async () => {
        await wrapper.setProps({
            optionsShow: true,
            selectable: true,
            items: [
                { id: "1", label: "folder1", isLeaf: false, selectionState: SELECTION_STATES.MIXED },
                { id: "2", label: "file2", isLeaf: true, selectionState: SELECTION_STATES.UNSELECTED },
            ],
        });

        const rowCheckbox = wrapper.find("tbody tr[aria-rowindex='1'] .g-table-select-column input").element;
        expect(rowCheckbox.checked).toBe(false);
        expect(rowCheckbox.indeterminate).toBe(true);
    });

    it("emits onClick for the row when its checkbox is toggled", async () => {
        await wrapper.setProps({
            optionsShow: true,
            selectable: true,
            items: [
                { id: "1", label: "folder1", isLeaf: false, selectionState: SELECTION_STATES.MIXED },
                { id: "2", label: "file2", isLeaf: true, selectionState: SELECTION_STATES.UNSELECTED },
            ],
        });

        const rowCheckbox = wrapper.find("tbody tr[aria-rowindex='1'] .g-table-select-column input");
        await rowCheckbox.trigger("change");

        expect(wrapper.emitted("onClick")).toBeTruthy();
        expect(emittedArg(wrapper, "onClick").id).toBe("1");
    });

    it("emits onClick exactly once when a selectable row is clicked", async () => {
        await wrapper.setProps({
            optionsShow: true,
            selectable: true,
            items: [{ id: "1", label: "file1", isLeaf: true, selectionState: SELECTION_STATES.UNSELECTED }],
        });

        // GTable emits both "row-select" and "row-click" for a selectable row;
        // SelectionDialog must not toggle selection twice.
        await wrapper.find("tbody tr[aria-rowindex='1']").trigger("click");

        expect(wrapper.emitted("onClick")).toBeTruthy();
        expect(wrapper.emitted("onClick")).toHaveLength(1);
    });

    it("formats the time column from the item's updateTime and shows - when it is missing", async () => {
        const updateTime = new Date("2026-10-17T09:30:00");
        await wrapper.setProps({
            optionsShow: true,
            fields: [
                { key: "label", label: "Name" },
                { key: "time", label: "Time" },
            ],
            items: [
                { id: "1", label: "file1", isLeaf: true, time: "2026-10-17T09:30:00", updateTime },
                { id: "2", label: "file2", isLeaf: true, time: "not a date" },
            ],
        });

        const cells = wrapper.findAll("td[id^='g-table-cell-time-']");
        expect(cells).toHaveLength(2);
        expect(nth(cells, 0).text()).toBe(
            updateTime.toLocaleString("default", {
                day: "numeric",
                month: "short",
                year: "numeric",
                minute: "numeric",
                hour: "numeric",
            }),
        );
        expect(nth(cells, 1).text()).toBe("-");
    });

    it("filters on the displayed values, not on the parsed time or the raw entry", async () => {
        await wrapper.setProps({
            optionsShow: true,
            items: [
                {
                    id: "1",
                    label: "reads.fastq",
                    isLeaf: true,
                    selectionState: SELECTION_STATES.UNSELECTED,
                    updateTime: new Date("2026-10-17T09:30:00Z"),
                    entry: { id: "1" },
                },
            ],
        });
        const search = wrapper.findComponent(DataDialogSearch);
        const rows = () => wrapper.findAll("td[id^='g-table-cell-label-']");

        for (const text of ["gmt", "object", "unselected"]) {
            search.vm.$emit("input", text);
            await nextTick();
            expect(rows()).toHaveLength(0);
        }

        search.vm.$emit("input", "reads");
        await nextTick();
        expect(rows()).toHaveLength(1);
    });
});
