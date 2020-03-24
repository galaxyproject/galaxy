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
            },
            stubs: {
                "tree-options": "<div id='tree-options'/>",
                "cool-search": "<div id='cool-search'/>",
            },
            propsData: mockOptions,
            localVue,
        });
    });

    it("loads correctly in loading state, shows options when optionsShow becomes true", async () => {
        expect(wrapper.find(".fa-spinner").text()).to.equals("");
        expect(wrapper.contains(".fa-spinner")).to.equals(true);
        expect(wrapper.contains("#tree-options")).to.equals(false);
        wrapper.setProps({ optionsShow: true });
        await localVue.nextTick();
        expect(wrapper.contains(".fa-spinner")).to.equals(false);
        expect(wrapper.contains("#tree-options")).to.equals(true);
    });

    it("loads search correctly", async () => {
        await localVue.nextTick();
        expect(wrapper.contains("#cool-search")).to.equals(true);
    });

    it("hideModal called on click cancel", async () => {
        expect(calledHide).to.equals(false);
        expect(wrapper.contains(".selection-dialog-modal-cancel")).to.equals(true);
        wrapper.setProps({ optionsShow: true });
        await localVue.nextTick();
        wrapper.find(".selection-dialog-modal-cancel").trigger("click");
        await localVue.nextTick();
        expect(calledHide).to.equals(true);
    });
});
