import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import { setActivePinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import { useToolStore } from "@/stores/toolStore";

import { createWhooshQuery } from "../Panels/utilities";

import ToolsList from "./ToolsList.vue";

const FILTER_INPUTS = {
    "[placeholder='any name']": "name-filter",
    "[placeholder='any section']": "section-filter",
    "[placeholder='any EDAM ontology']": "ontology-filter",
    "[placeholder='any id']": "id-filter",
    "[placeholder='any repository owner']": "owner-filter",
    "[placeholder='any help text']": "help-filter",
};
const FILTER_SETTINGS = {
    name: "name-filter",
    section: "section-filter",
    ontology: "ontology-filter",
    id: "id-filter",
    owner: "owner-filter",
    help: "help-filter",
};
const WHOOSH_QUERY = createWhooshQuery(FILTER_SETTINGS);

const routerPushMock = jest.fn();

jest.mock("vue-router/composables", () => ({
    useRouter: () => ({
        push: routerPushMock,
    }),
}));

const localVue = getLocalVue();

describe("ToolsList", () => {
    let fetchToolsMock: jest.SpyInstance;
    let pinia: ReturnType<typeof createTestingPinia>;

    beforeEach(() => {
        pinia = createTestingPinia({ stubActions: false });
        setActivePinia(pinia);

        const toolStore = useToolStore(pinia);
        fetchToolsMock = jest.spyOn(toolStore, "fetchTools").mockResolvedValue();
        jest.spyOn(toolStore, "fetchToolSections").mockResolvedValue();

        // Clear the router mock between tests
        routerPushMock.mockClear();
    });

    it("performs an advanced search with a router push", async () => {
        const wrapper = mount(ToolsList as object, {
            localVue,
            pinia,
        });

        // By default, no search text, fetch tools is still called but without a query
        expect(fetchToolsMock).toHaveBeenCalledWith("");

        expect(wrapper.find("[data-description='toggle advanced search']").exists()).toBe(true);

        await wrapper.find("[data-description='toggle advanced search']").trigger("click");

        expect(wrapper.find("[data-description='advanced filters']").exists()).toBe(true);

        const sectionField = wrapper.find("[placeholder='any section']");
        await sectionField.trigger("keyup.esc");

        // Add filters to fields
        await wrapper.find("[data-description='toggle advanced search']").trigger("click");

        // Now add all filters in the advanced menu
        for (const [selector, value] of Object.entries(FILTER_INPUTS)) {
            const filterInput = wrapper.find(selector);
            expect(filterInput.vm).toBeTruthy();
            expect(filterInput.props().type).toBe("text");
            await filterInput.setValue(value);
        }

        // Test: we route to the list with filters
        await wrapper.find("[data-description='apply filters']").trigger("click");

        expect(routerPushMock).toHaveBeenCalledWith({
            path: "/tools/list",
            query: FILTER_SETTINGS,
        });
    });

    it("detects filters in the route and searches the backend", async () => {
        mount(ToolsList as object, {
            localVue,
            pinia,
            propsData: FILTER_SETTINGS,
        });

        expect(fetchToolsMock).toHaveBeenCalledWith(WHOOSH_QUERY);
    });
});
