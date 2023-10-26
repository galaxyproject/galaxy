// test response
import { shallowMount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import testToolsListResponse from "../testData/toolsList";
import testToolsListInPanelResponse from "../testData/toolsListInPanel";
import ToolsJson from "./ToolsJson";

const localVue = getLocalVue();

describe("ToolSchemaJson/ToolsView.vue", () => {
    let wrapper;
    let axiosMock;
    const defaultSchemaElementTag = "application/ld+json";

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
        axiosMock.onGet("/api/tools?in_panel=False&tool_help=True").reply(200, testToolsListResponse);
        axiosMock.onGet("/api/tool_panels/default").reply(200, testToolsListInPanelResponse);
        wrapper = shallowMount(ToolsJson, { localVue });
        await flushPromises();
    });

    it("schema.org script element is created", async () => {
        const toolsList = testToolsListResponse.reduce((acc, item) => {
            acc[item.id] = item;
            return acc;
        }, {});
        const toolsListInPanel = testToolsListInPanelResponse;
        const tools = wrapper.vm.createToolsJson(toolsList, toolsListInPanel);
        const schemaElement = document.getElementById("schema-json");
        const schemaText = JSON.parse(schemaElement.text);
        expect(tools["@graph"].length === 5).toBeTruthy();
        expect(schemaText["@graph"].length === 5).toBeTruthy();
        expect(schemaElement.type === defaultSchemaElementTag).toBeTruthy();
    });
});
