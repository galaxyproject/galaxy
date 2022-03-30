import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import HistoryFilters from "./HistoryFilters";
const localVue = getLocalVue();

describe("HistoryFilters", () => {
    it("test history filter panel", async () => {
        const wrapper = mount(HistoryFilters, {
            propsData: {
                filterText: "",
                showAdvanced: false,
            },
            localVue,
            stubs: {
                icon: { template: "<div></div> " },
            },
        });
        expect(wrapper.findAll("[description='advanced filters']").length).toBe(0);
        await wrapper.setProps({ showAdvanced: true });
        expect(wrapper.findAll("[description='advanced filters']").length).toBe(1);
        const filterInputs = {
            "[placeholder='any name']": "name-filter",
            "[placeholder='any extension']": "ext-filter",
            "[placeholder='any tag']": "tag filter",
            "[placeholder='any state']": "state-filter",
            "[placeholder='index greater']": "hid-greater",
            "[placeholder='index lower']": "hid-lower",
            "[placeholder='created after']": "January 1, 2022",
            "[placeholder='created before']": "January 1, 2023",
        };
        Object.entries(filterInputs).forEach(([selector, value]) => {
            const filterInput = wrapper.find(selector);
            if (filterInput.vm && filterInput.props().type == "text") {
                filterInput.setValue(value);
            }
        });
        const searchButton = wrapper.findAll("[description='apply filters']");
        await searchButton.trigger("click");
        const emitted = wrapper.emitted();
        expect(emitted["update:show-advanced"][0][0]).toEqual(false);
        const filterValidation = [
            "name=name-filter",
            "extension=ext-filter",
            "tag='tag filter'",
            "state=state-filter",
            "hid>hid-greater",
            "hid<hid-lower",
        ];
        filterValidation.forEach((filterValue) => {
            expect(emitted["update:filter-text"][0][0]).toContain(filterValue);
        });
    });
});
