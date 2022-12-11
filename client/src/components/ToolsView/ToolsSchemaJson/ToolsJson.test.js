import ToolsJson from "./ToolsJson";
// test response
import testToolsListResponse from "../testData/toolsList";
import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import flushPromises from "flush-promises";

const localVue = getLocalVue();

describe("ToolSchemaJson/ToolsView.vue", () => {
    let wrapper;
    let axiosMock;
    const defaultSchemaElementTag = "application/ld+json";

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
        axiosMock.onGet("/api/tools?tool_help=True").reply(200, testToolsListResponse);
        wrapper = shallowMount(ToolsJson, { localVue });
        await flushPromises();
    });

    it("schema.org script element is created", async () => {
        const tools = wrapper.vm.createToolsJson(testToolsListResponse);
        const schemaElement = document.getElementById("schema-json");
        const schemaText = JSON.parse(schemaElement.text);
        expect(tools["@graph"].length === 5).toBeTruthy();
        expect(schemaText["@graph"].length === 5).toBeTruthy();
        expect(schemaElement.type === defaultSchemaElementTag).toBeTruthy();
    });
});
