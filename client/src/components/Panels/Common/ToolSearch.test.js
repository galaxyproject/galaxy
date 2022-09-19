import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import ToolSearch from "./ToolSearch";
const localVue = getLocalVue();

describe("ToolSearch", () => {
    it("test tools advanced filter panel", async () => {
        const wrapper = mount(ToolSearch, {
            propsData: {
                currentPanelView: "default",
                showAdvanced: false,
            },
            localVue,
            stubs: {
                icon: { template: "<div></div>" },
            },
        });

        expect(wrapper.find("[description='advanced tool filters']").exists()).toBe(false);
        await wrapper.setProps({ showAdvanced: true });
        expect(wrapper.find("[description='advanced tool filters']").exists()).toBe(true);
        const filterInputs = {
            "[placeholder='any tool name']": "name-filter",
            "[placeholder='any section']": "section-filter",
            "[placeholder='any id']": "id-filter",
            "[placeholder='any description']": "desc-filter",
        };

        // Now add filters in all input fields in the advanced menu
        Object.entries(filterInputs).forEach(([selector, value]) => {
            const filterInput = wrapper.find(selector);
            if (filterInput.vm && filterInput.props().type == "text") {
                filterInput.setValue(value);
            }
        });

        // Test: values are stored in the filterSettings object
        expect(Object.values(wrapper.vm.filterSettings)).toEqual(Object.values(filterInputs));

        // Test: clearing the filters
        const clearButton = wrapper.find("[description='clear filters']");
        expect(Object.values(wrapper.vm.filterSettings).length).toBe(4);
        await clearButton.trigger("click");
        expect(Object.values(wrapper.vm.filterSettings).length).toBe(0);

        // Test: keyup.esc (should toggle the view out)
        const nameField = wrapper.find("[placeholder='any tool name']");
        expect(wrapper.emitted()["update:show-advanced"]).toBeUndefined();
        await nameField.trigger("keyup.esc");
        expect(wrapper.emitted()["update:show-advanced"].length - 1).toBeFalsy();
    });
});
