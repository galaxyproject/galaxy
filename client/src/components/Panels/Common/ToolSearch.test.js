import "jest-location-mock";

import { mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { getLocalVue, injectTestRouter } from "tests/jest/helpers";

import ToolSearch from "./ToolSearch";

const globalConfig = getLocalVue();
const router = injectTestRouter();

describe("ToolSearch", () => {
    it("test tools advanced filter panel navigation", async () => {
        const pinia = createPinia();
        const wrapper = mount(ToolSearch, {
            props: {
                currentPanelView: "default",
                enableAdvanced: false,
                showAdvanced: false,
                toolsList: [],
                currentPanel: {},
                useWorker: false,
            },
            global: {
                ...globalConfig.global,
                plugins: [...globalConfig.global.plugins, pinia, router],
                stubs: {
                    icon: { template: "<div></div>" },
                },
            },
        });
        const $router = wrapper.vm.$router;

        expect(wrapper.find("[data-description='toggle advanced search']").exists()).toBe(false);
        expect(wrapper.find("[description='advanced filters']").exists()).toBe(false);
        await wrapper.setProps({ enableAdvanced: true, showAdvanced: true });
        expect(wrapper.find("[data-description='wide toggle advanced search']").exists()).toBe(true);
        expect(wrapper.find("[data-description='advanced filters']").exists()).toBe(true);

        // Test: keyup.esc (should toggle the view out) --- doesn't work from name (DelayedInput) field
        const sectionField = wrapper.find("[placeholder='any section']");
        expect(wrapper.emitted("update:show-advanced")).toBeUndefined();
        await sectionField.trigger("keyup.esc");
        const emitted = wrapper.emitted("update:show-advanced");
        expect(emitted ? emitted.length - 1 : 0).toBeFalsy();

        // Add filters to fields
        await wrapper.find("[data-description='toggle advanced search']").trigger("click");
        // await wrapper.setProps({ showAdvanced: true });
        const filterInputs = {
            "[placeholder='any name']": "name-filter",
            "[placeholder='any section']": "section-filter",
            "[placeholder='any EDAM ontology']": "ontology-filter",
            "[placeholder='any id']": "id-filter",
            "[placeholder='any repository owner']": "owner-filter",
            "[placeholder='any help text']": "help-filter",
        };

        // Now add all filters in the advanced menu
        for (const [selector, value] of Object.entries(filterInputs)) {
            const filterInput = wrapper.find(selector);
            if (filterInput.exists() && filterInput.element) {
                filterInput.element.value = value;
                await filterInput.trigger("input");
            }
        }

        // Test: we route to the list with filters
        const mockMethod = jest.fn();
        $router.push = mockMethod;
        await wrapper.find("[data-description='apply filters']").trigger("click");
        const filterSettings = {
            name: "name-filter",
            section: "section-filter",
            ontology: "ontology-filter",
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
