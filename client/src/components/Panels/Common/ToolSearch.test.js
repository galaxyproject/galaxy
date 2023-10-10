import "jest-location-mock";

import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import VueRouter from "vue-router";

import ToolSearch from "./ToolSearch";

const localVue = getLocalVue();
localVue.use(VueRouter);
const router = new VueRouter();

describe("ToolSearch", () => {
    it("test tools advanced filter panel", async () => {
        const wrapper = mount(ToolSearch, {
            propsData: {
                currentPanelView: "default",
                enableAdvanced: false,
                showAdvanced: false,
                toolbox: [],
            },
            localVue,
            router,
            stubs: {
                icon: { template: "<div></div>" },
            },
        });
        const $router = wrapper.vm.$router;

        expect(wrapper.find("[data-description='toggle advanced search']").exists()).toBe(false);
        expect(wrapper.find("[description='advanced filters']").exists()).toBe(false);
        await wrapper.setProps({ enableAdvanced: true, showAdvanced: true });
        expect(wrapper.find("[data-description='wide toggle advanced search']").exists()).toBe(true);
        expect(wrapper.find("[data-description='advanced filters']").exists()).toBe(true);

        // Test: changing panel view should change search by section field to search by ontology
        expect(wrapper.find("[placeholder='any section']").exists()).toBe(true);
        await wrapper.setProps({ currentPanelView: "ontology:edam_operations" });
        expect(wrapper.find("[placeholder='any section']").exists()).toBe(false);
        expect(wrapper.find("[placeholder='any ontology']").exists()).toBe(true);
        await wrapper.setProps({ currentPanelView: "default" });

        // Test: keyup.esc (should toggle the view out) --- doesn't work from name (DelayedInput) field
        const sectionField = wrapper.find("[placeholder='any section']");
        expect(wrapper.emitted()["update:show-advanced"]).toBeUndefined();
        await sectionField.trigger("keyup.esc");
        expect(wrapper.emitted()["update:show-advanced"].length - 1).toBeFalsy();

        // Add filters to fields
        await wrapper.find("[data-description='toggle advanced search']").trigger("click");
        // await wrapper.setProps({ showAdvanced: true });
        const filterInputs = {
            "[placeholder='any name']": "name-filter",
            "[placeholder='any section']": "section-filter",
            "[placeholder='any id']": "id-filter",
            "[placeholder='any repository owner']": "owner-filter",
            "[placeholder='any help text']": "help-filter",
        };

        // Now add all filters in the advanced menu
        Object.entries(filterInputs).forEach(([selector, value]) => {
            const filterInput = wrapper.find(selector);
            if (filterInput.vm && filterInput.props().type == "text") {
                filterInput.setValue(value);
            }
        });

        // Test: we route to the list with filters
        const mockMethod = jest.fn();
        $router.push = mockMethod;
        await wrapper.find("[data-description='apply filters']").trigger("click");
        const filterSettings = {
            name: "name-filter",
            section: "section-filter",
            id: "id-filter",
            owner: "owner-filter",
            help: "help-filter",
        };
        expect(mockMethod).toHaveBeenCalledWith({
            path: "/tools/list",
            query: filterSettings,
        });
    });
});
