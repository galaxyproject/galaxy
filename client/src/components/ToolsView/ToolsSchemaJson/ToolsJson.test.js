import ToolsJson from "./ToolsJson";
// test response
import testToolsListResponse from "../testData/toolsList";
import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import Vue from "vue";
import { mount } from "@vue/test-utils";

describe("ToolsView/ToolsView.vue", () => {
    let wrapper, axiosMock;
    const defaultSchemaElementTag = "application/ld+json";

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
        wrapper = mount(ToolsJson);
        axiosMock.onGet("/api/tools?tool_help=True").reply(200, testToolsListResponse);
        await Vue.nextTick();
    });

    it("schema.org script element is created", async () => {
        await Vue.nextTick();
        const tools = wrapper.vm.createToolsJson(testToolsListResponse);
        const schemaElement = document.getElementById("schema-json");
        const schemaText = JSON.parse(schemaElement.text);
        assert(tools["@graph"].length === 84, "tools are not parsed correctly!");
        assert(schemaText["@graph"].length === 84, "tools are not correctly presented in schema script tag!");
        assert(schemaElement.type === defaultSchemaElementTag, "element type is not correct!");
    });
});
