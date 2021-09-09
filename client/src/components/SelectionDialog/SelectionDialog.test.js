import SelectionDialog from "./SelectionDialog.vue";
import { mount, createLocalVue } from "@vue/test-utils";

const mockOptions = {
    callback: () => {},
    modalStatic: true,
};

describe("SelectionDialog.vue", () => {
    let wrapper;
    let localVue;
    let calledHide = false;

    beforeEach(() => {
        localVue = createLocalVue();
        mockOptions.hideModal = () => {
            calledHide = true;
        };
        wrapper = mount(SelectionDialog, {
            slots: {
                options: "<tree-options />",
                search: "<cool-search />",
                selectAll: "<select-all />",
            },
            stubs: {
                "tree-options": { template: "<div id='tree-options'/>" },
                "cool-search": { template: "<div id='cool-search'/>" },
                "select-all": { template: "<div id='select-all'/>" },
            },
            propsData: mockOptions,
            localVue,
        });
    });

    it("loads correctly in loading state, shows options when optionsShow becomes true", async () => {
        expect(wrapper.get(".fa-spinner"));
        expect(wrapper.get(".fa-spinner").text()).toBe("");
        //expect(wrapper.get("#tree-options")).toThrow();
        wrapper.setProps({ optionsShow: true });
        await localVue.nextTick();
        expect(() => wrapper.get(".fa-spinner")).toThrow();
        expect(wrapper.get("#tree-options"));
    });

    it("loads header correctly", async () => {
        await localVue.nextTick();
        expect(wrapper.get("#cool-search"));
    });

    it("hideModal called on click cancel", async () => {
        expect(calledHide).toBe(false);
        expect(wrapper.get(".selection-dialog-modal-cancel"));
        wrapper.setProps({ optionsShow: true });
        await localVue.nextTick();
        wrapper.find(".selection-dialog-modal-cancel").trigger("click");
        await localVue.nextTick();
        expect(calledHide).toBe(true);
    });
});
