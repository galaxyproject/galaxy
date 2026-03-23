import { createLocalVue, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it } from "vitest";

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
});
