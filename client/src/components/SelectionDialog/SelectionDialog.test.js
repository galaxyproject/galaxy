import { createLocalVue, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it } from "vitest";

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
        localVue = createLocalVue();
        wrapper = mount(SelectionDialog, {
            propsData: mockOptions,
            localVue,
        });
    });

    it("loads correctly in loading state, shows options when optionsShow becomes true", async () => {
        expect(wrapper.find("[data-description='selection dialog spinner']").exists()).toBeTruthy();
        expect(wrapper.findComponent(GTable).exists()).toBeFalsy();
        await wrapper.setProps({ optionsShow: true });
        expect(wrapper.find("[data-description='selection dialog spinner']").exists()).toBeFalsy();
        expect(wrapper.findComponent(GTable).exists()).toBeTruthy();
    });

    it("loads header correctly", async () => {
        await localVue.nextTick();
        expect(wrapper.findComponent(DataDialogSearch).exists()).toBeTruthy();
    });

    it("hideModal called on click cancel", async () => {
        expect(wrapper.emitted().onCancel).toBeFalsy();
        wrapper.find("[data-description='selection dialog cancel']").trigger("click");
        expect(wrapper.emitted().onCancel).toBeTruthy();
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

        expect(wrapper.emitted().onClick).toBeTruthy();
        expect(wrapper.emitted().onClick[0][0].id).toBe("1");
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

        expect(wrapper.emitted().onClick).toBeTruthy();
        expect(wrapper.emitted().onClick.length).toBe(1);
    });
});
