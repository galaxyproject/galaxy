import { mount } from "@vue/test-utils";
import { BTable } from "bootstrap-vue";
import { getLocalVue } from "tests/jest/helpers";

import DataDialogSearch from "./DataDialogSearch.vue";
import SelectionDialog from "./SelectionDialog.vue";

const globalConfig = getLocalVue();

const mockOptions = {
    callback: () => {},
    modalShow: true,
    modalStatic: true,
};

describe("SelectionDialog.vue", () => {
    let wrapper;

    beforeEach(() => {
        wrapper = mount(SelectionDialog, {
            props: mockOptions,
            global: globalConfig.global,
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
        await wrapper.vm.$nextTick();
        expect(wrapper.findComponent(DataDialogSearch).exists()).toBeTruthy();
    });

    it("hideModal called on click cancel", async () => {
        expect(wrapper.emitted().onCancel).toBeFalsy();
        wrapper.find("[data-description='selection dialog cancel']").trigger("click");
        expect(wrapper.emitted().onCancel).toBeTruthy();
    });
});
