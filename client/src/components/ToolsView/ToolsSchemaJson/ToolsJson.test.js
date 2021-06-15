import ToolsJson from "./ToolsJson";
// test response
import testToolsListResponse from "../testData/toolsList";
import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";

const localVue = getLocalVue();

describe("ToolsView/ToolsView.vue", () => {
    let wrapper;
    let axiosMock;
    const defaultSchemaElementTag = "application/ld+json";

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
        wrapper = shallowMount(ToolsJson, { localVue });
        axiosMock.onGet("/api/tools?tool_help=True").reply(200, testToolsListResponse);
        await wrapper.vm.$nextTick();
    });

    it("schema.org script element is created", async () => {
        await wrapper.vm.$nextTick();
        const tools = wrapper.vm.createToolsJson(testToolsListResponse);
        const schemaElement = document.getElementById("schema-json");
        const schemaText = JSON.parse(schemaElement.text);
        expect(tools["@graph"].length === 5).toBeTruthy();
        expect(schemaText["@graph"].length === 5).toBeTruthy();
        expect(schemaElement.type === defaultSchemaElementTag).toBeTruthy();
    });
});
