import { mount } from "@vue/test-utils";
import { getLocalVue, mountRenderless } from "jest/helpers";
import ToolSearch from "./ToolSearch";
import { getAppRoot } from "onload/loadConfig";
import DelayedInput from "components/Common/DelayedInput";

jest.mock("onload/loadConfig");
getAppRoot.mockImplementation(() => "/");

jest.mock("axios");

const localVue = getLocalVue();

describe("ToolSearch", () => {
    let tools;
    let store;
    
    const testCase = {
        keyword: "bed" /* examples: gff2bed1, bed2gff1, wig_to_bigWig */
    };

    beforeEach(async () => {
    });

    test("test tool search get results", () => {
        let wrapper = mount(ToolSearch, {
            propsData: {
                category: {
                    name: "name",
                },
                toolbox: tools,
                storedWorkflowMenuEntries: [],
                currentPanelView: 'default',
                query: testCase.keyword,
            }, 
            localVue,
            stubs: {
                icon: { template: "<div></div>" },
            },
            store
        });
    });

    it("test tool search returns results", async () => {
    });
});
