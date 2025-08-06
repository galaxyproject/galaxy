import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import { setActivePinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import { useToolStore } from "@/stores/toolStore";

import { createWhooshQuery } from "../Panels/utilities";

import ToolsList from "./ToolsList.vue";

const localVue = getLocalVue();

describe("ToolsList", () => {
    it("test tools advanced filter panel navigation", async () => {
        const pinia = createTestingPinia({ stubActions: false });
        setActivePinia(pinia);

        const toolStore = useToolStore(pinia);
        const fetchToolsMock = jest.spyOn(toolStore, "fetchTools").mockResolvedValue();

        const wrapper = mount(ToolsList as object, {
            localVue,
            pinia,
        });

        expect(wrapper.find("[data-description='toggle advanced search']").exists()).toBe(true);

        await wrapper.find("[data-description='toggle advanced search']").trigger("click");

        expect(wrapper.find("[data-description='advanced filters']").exists()).toBe(true);

        const sectionField = wrapper.find("[placeholder='any section']");
        await sectionField.trigger("keyup.esc");

        // Add filters to fields
        await wrapper.find("[data-description='toggle advanced search']").trigger("click");
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
            expect(filterInput.vm).toBeTruthy();
            expect(filterInput.props().type).toBe("text");
            await filterInput.setValue(value);
        }

        // Test: we route to the list with filters
        await wrapper.find("[data-description='apply filters']").trigger("click");

        const filterSettings = {
            name: "name-filter",
            section: "section-filter",
            ontology: "ontology-filter",
            id: "id-filter",
            owner: "owner-filter",
            help: "help-filter",
        };
        const whooshQuery = createWhooshQuery(filterSettings);

        expect(fetchToolsMock).toHaveBeenCalledWith(whooshQuery);
    });
});
