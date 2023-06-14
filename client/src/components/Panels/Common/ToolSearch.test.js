import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import DelayedInput from "components/Common/DelayedInput";
import ToolSearch from "./ToolSearch";
import VueRouter from "vue-router";
import "jest-location-mock";

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
        expect(wrapper.find("[description='advanced tool filters']").exists()).toBe(false);
        await wrapper.setProps({ enableAdvanced: true, showAdvanced: true });
        expect(wrapper.find("[data-description='toggle advanced search']").exists()).toBe(true);
        expect(wrapper.find("[description='advanced tool filters']").exists()).toBe(true);

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
        await wrapper.setProps({ showAdvanced: true });
        const filterInputs = {
            name: "name-filter",
            "[placeholder='any section']": "section-filter",
            "[placeholder='any id']": "id-filter",
            "[placeholder='any owner']": "owner-filter",
            "[placeholder='any help text']": "help-filter",
        };

        // Add name filter (comes from DelayedInput emitting the query prop)
        wrapper.findComponent(DelayedInput).vm.$emit("change", filterInputs["name"]);

        // Now add remaining filters (other than name) in the advanced menu
        Object.entries(filterInputs).forEach(([selector, value]) => {
            const filterInput = wrapper.find(selector);
            if (filterInput.vm && filterInput.props().type == "text") {
                filterInput.setValue(value);
            }
        });

        // Test: we route to the list with filters
        const mockMethod = jest.fn();
        $router.push = mockMethod;
        wrapper.find(".filter-search-btn").trigger("click");
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
