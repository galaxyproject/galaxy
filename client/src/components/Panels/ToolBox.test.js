import { createPinia } from "pinia";
import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import { filterToolSections, filterTools } from "./utilities";
import ToolBox from "./ToolBox";
import toolsList from "./testToolsList";
import { useConfig } from "composables/config";

jest.mock("composables/config");
useConfig.mockReturnValue({
    config: {
        toolbox_auto_sort: true,
    },
    isLoaded: true,
});

const localVue = getLocalVue();

describe("ToolBox", () => {
    const toolsMock = toolsList;
    const resultsMock = ["join1", "join_collections", "find1"];
    let axiosMock;

    const searches = {
        join: ["join1", "join_collections", "find1"],
        find: ["find1"],
        remove: ["remove1", "remove_duplicate"],
        fi: null,
    };

    let wrapper;

    beforeEach(async () => {
        const pinia = createPinia();
        axiosMock = new MockAdapter(axios);

        wrapper = mount(ToolBox, {
            propsData: {
                toolbox: toolsList,
                currentPanelView: "default",
                storedWorkflowMenuEntries: [],
            },
            localVue,
            stubs: {
                icon: { template: "<div></div>" },
            },
            pinia,
        });
    });

    it("test filter functions correctly matching: (1) Tools store array-of-objects with (2) Results array", async () => {
        axiosMock
            .onGet(`/api/tools`)
            .replyOnce(200, toolsMock)
            .onGet(/api\/tools?.*/)
            .replyOnce(200, resultsMock);
        const toolsResults = filterTools(toolsMock, resultsMock);
        const toolsResultsSection = filterToolSections(toolsMock, resultsMock);
        expect(toolsResults.length).toBe(3);
        expect(toolsResultsSection.length).toBe(2);
    });

    it("test toolbox client search", async () => {
        for (const [query, results] of Object.entries(searches)) {
            await wrapper.setData({ query: query });
            expect(wrapper.vm.results).toEqual(results);
        }
    });
});
