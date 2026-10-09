import { emittedArg, getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import { SELECTION_STATES } from "./selectionTypes";

import DataDialogSearch from "./DataDialogSearch.vue";
import SelectionDialog from "./SelectionDialog.vue";
import GTable from "@/components/Common/GTable.vue";

enableAutoUnmount(afterEach);

function mountSelectionDialog() {
    return mount(SelectionDialog, {
        props: { modalShow: true },
        global: getLocalVue(),
    });
}

describe("SelectionDialog.vue", () => {
    it("replaces the loading spinner with options when optionsShow becomes true", async () => {
        const wrapper = mountSelectionDialog();
        expect(wrapper.find("[data-description='selection dialog spinner']").exists()).toBe(true);
        expect(wrapper.findComponent(GTable).exists()).toBe(false);
        await wrapper.setProps({ optionsShow: true });
        expect(wrapper.find("[data-description='selection dialog spinner']").exists()).toBe(false);
        expect(wrapper.findComponent(GTable).exists()).toBe(true);
    });

    it("renders the search header", () => {
        const wrapper = mountSelectionDialog();
        expect(wrapper.findComponent(DataDialogSearch).exists()).toBe(true);
    });

    it("emits onCancel when the cancel button is clicked", async () => {
        const wrapper = mountSelectionDialog();
        expect(wrapper.emitted("onCancel")).toBeUndefined();
        await wrapper.find("[data-description='selection dialog cancel']").trigger("click");
        expect(wrapper.emitted("onCancel")).toHaveLength(1);
    });

    it("syncs row selection state from incoming items", async () => {
        const wrapper = mountSelectionDialog();
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
        const wrapper = mountSelectionDialog();
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
        const wrapper = mountSelectionDialog();
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
        const wrapper = mountSelectionDialog();
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

        expect(wrapper.emitted("onClick")).toBeDefined();
        expect(emittedArg(wrapper, "onClick").id).toBe("1");
    });

    it("emits onClick exactly once when a selectable row is clicked", async () => {
        const wrapper = mountSelectionDialog();
        await wrapper.setProps({
            optionsShow: true,
            selectable: true,
            items: [{ id: "1", label: "file1", isLeaf: true, selectionState: SELECTION_STATES.UNSELECTED }],
        });

        // GTable emits both "row-select" and "row-click" for a selectable row;
        // SelectionDialog must not toggle selection twice.
        await wrapper.find("tbody tr[aria-rowindex='1']").trigger("click");

        expect(wrapper.emitted("onClick")).toBeDefined();
        expect(wrapper.emitted("onClick")).toHaveLength(1);
    });
});
