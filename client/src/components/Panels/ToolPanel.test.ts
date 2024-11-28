import "jest-location-mock";

import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import toolsList from "@/components/ToolsView/testData/toolsList.json";
import toolsListInPanel from "@/components/ToolsView/testData/toolsListInPanel.json";

import viewsList from "./testData/viewsList.json";
import { types_to_icons } from "./utilities";

import ToolPanel from "./ToolPanel.vue";

const localVue = getLocalVue();

const TEST_PANELS_URI = "/api/tool_panels";

jest.mock("@/composables/config", () => ({
    useConfig: jest.fn(() => ({
        config: {},
        isConfigLoaded: true,
    })),
}));

describe("ToolPanel", () => {
    it("test navigation of tool panel views menu", async () => {
        const axiosMock = new MockAdapter(axios);
        axiosMock
            .onGet(/\/api\/tool_panels\/.*/)
            .reply(200, toolsListInPanel)
            .onGet(`/api/tools?in_panel=False`)
            .replyOnce(200, toolsList)
            .onGet(TEST_PANELS_URI)
            .reply(200, { default_panel_view: "default", views: viewsList });

        const pinia = createPinia();
        const wrapper = mount(ToolPanel as object, {
            propsData: {
                workflow: false,
                editorWorkflows: null,
                dataManagers: null,
                moduleSections: null,
            },
            localVue,
            stubs: {
                icon: { template: "<div></div>" },
                ToolBox: true,
            },
            pinia,
        });

        await flushPromises();

        // there is a panel view selector initially collapsed
        expect(wrapper.find(".panel-view-selector").exists()).toBe(true);
        expect(wrapper.find(".dropdown-menu.show").exists()).toBe(false);

        // Test: starts up with a default panel view, click to open menu
        expect(wrapper.find("#toolbox-heading").text()).toBe("Tools");
        await wrapper.find("#toolbox-heading").trigger("click");
        await flushPromises();

        const dropdownMenu = wrapper.find(".dropdown-menu.show");
        expect(dropdownMenu.exists()).toBe(true);

        // Test: check if the dropdown menu has all the panel views
        const dropdownItems = dropdownMenu.findAll(".dropdown-item");
        expect(dropdownItems.length).toEqual(Object.keys(viewsList).length);

        // Test: click on each panel view, and check if the panel view is changed
        for (const [key, value] of Object.entries(viewsList)) {
            // find dropdown item
            const currItem = dropdownMenu.find(`[data-panel-id='${key}']`);
            if (key !== "default") {
                // Test: check if the panel view has appropriate description
                const description = currItem.attributes().title || null;
                expect(description).toBe(value.description);

                // set current panel view
                await currItem.trigger("click");
                await flushPromises();

                // Test: check if the current panel view is selected now
                expect(currItem.find(".fa-check").exists()).toBe(true);

                // Test: check if the panel header now has an icon and a changed name
                const panelViewIcon = wrapper.find("[data-description='panel view header icon']");
                expect(panelViewIcon.classes()).toContain(
                    `fa-${types_to_icons[value.view_type as keyof typeof types_to_icons]}`
                );
                expect(wrapper.find("#toolbox-heading").text()).toBe(value.name);
            } else {
                // Test: check if the default panel view is already selected, and no icon
                expect(currItem.find(".fa-check").exists()).toBe(true);
                expect(wrapper.find("[data-description='panel view header icon']").exists()).toBe(false);
            }
        }
    });
});
