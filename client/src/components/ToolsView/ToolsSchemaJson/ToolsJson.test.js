// test response
import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import testToolsListResponse from "../testData/toolsList";
import testToolsListInPanelResponse from "../testData/toolsListInPanel";

import ToolsJson from "./ToolsJson.vue";

const localVue = getLocalVue();
const { server, http } = useServerMock();

describe("ToolSchemaJson/ToolsView.vue", () => {
    let wrapper;
    const defaultSchemaElementTag = "application/ld+json";

    beforeEach(async () => {
        server.use(
            http.untyped.get("/api/tools", ({ request }) => {
                const url = new URL(request.url);
                if (url.searchParams.get("in_panel") === "False" && url.searchParams.get("tool_help") === "True") {
                    return HttpResponse.json(testToolsListResponse);
                }
                return HttpResponse.json([]);
            }),
            http.untyped.get("/api/tool_panels/default", () => {
                return HttpResponse.json(testToolsListInPanelResponse);
            }),
        );
        wrapper = shallowMount(ToolsJson, { global: localVue });
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
        expect(tools["@graph"].length).toBe(5);
        expect(schemaText["@graph"].length).toBe(5);
        expect(schemaElement.type).toBe(defaultSchemaElementTag);
    });
});
