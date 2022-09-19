import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import ToolBox from "./ToolBox";
import { checkQuery } from "./Common/ToolSearch";
import { getAppRoot } from "onload/loadConfig";
import DelayedInput from "components/Common/DelayedInput";

jest.mock("onload/loadConfig");
getAppRoot.mockImplementation(() => "/");

jest.mock("axios");

const localVue = getLocalVue();

describe("ToolBox", () => {
    let wrapper;
    let tools;
    let results;
    let store;
    
    const testCase = {
        keyword: "bed" /* examples: gff2bed1, bed2gff1, wig_to_bigWig */
    };
    
    beforeEach(async () => {
        wrapper = mount(ToolBox, {
            propsData: {
                category: {
                    name: "name",
                },
                toolbox: [],
                storedWorkflowMenuEntries: [],
                currentPanelView: 'default',
                query: testCase.keyword,
                DelayedInput: DelayedInput,
                getAppRoot: '/',
            }, 
            localVue,
            stubs: {
                favoritesButton: { template: "<div></div>" },
                DelayedInput: { template: "<div></div>" }, /* test pass, but no value */
                icon: { template: "<div></div>" },
            },
            store
        });

        let filterName = wrapper.find("[placeholder='search tools']"); /* change var name */
        if (filterName.vm && filterName.props().type == "text") {
            filterName.setValue(testCase.keyword); /* change var value */
        }
    });

    test("test tool search get results", () => {
        const queryInput = wrapper.find("[placeholder='search tools']"); 
        console.log('queryInput', queryInput.element.value);
        // expect(queryInput.element.value).toBe(testCase.keyword); /* cannot test while DelayedInput in stub mode */
    });

    it("test tool search returns results", async () => {
    });
});
