import { createLocalVue, mount } from "@vue/test-utils";
import { BTable } from "bootstrap-vue";
import { beforeEach, describe, expect, it } from "vitest";

import DataDialogSearch from "./DataDialogSearch.vue";
import SelectionDialog from "./SelectionDialog.vue";

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
        expect(wrapper.findComponent(BTable).exists()).toBeFalsy();
        await wrapper.setProps({ optionsShow: true });
        expect(wrapper.find("[data-description='selection dialog spinner']").exists()).toBeFalsy();
        expect(wrapper.findComponent(BTable).exists()).toBeTruthy();
    });

    it("loads header correctly", async () => {
        await localVue.nextTick();
        expect(wrapper.findComponent(DataDialogSearch).exists()).toBeTruthy();
    });

    it.each([
        { modalShow: true, expectedOpen: true },
        { modalShow: false, expectedOpen: false },
    ])("dialog open is $expectedOpen when mounted with modalShow $modalShow", async ({ modalShow, expectedOpen }) => {
        const dialogWrapper = mount(SelectionDialog, {
            propsData: { ...mockOptions, modalShow },
            localVue,
            attachTo: document.body,
        });
        await localVue.nextTick();
        expect(dialogWrapper.find("dialog").element.open).toBe(expectedOpen);
        dialogWrapper.destroy();
    });

    it("hideModal called on click cancel", async () => {
        expect(wrapper.emitted().onCancel).toBeFalsy();
        wrapper.find("[data-description='selection dialog cancel']").trigger("click");
        expect(wrapper.emitted().onCancel).toBeTruthy();
    });
});
