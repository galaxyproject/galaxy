import "@/composables/__mocks__/filter";

import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import FormTool from "./FormTool.vue";

vi.mock("@/api/schema", () => ({}));

vi.mock("@/composables/config", () => ({
    useConfig: vi.fn(() => ({
        config: { enable_tool_source_display: false },
        isConfigLoaded: true,
    })),
}));

const localVue = getLocalVue();

const { server, http } = useServerMock();

describe("FormTool", () => {
    beforeEach(() => {
        server.use(
            http.get("/api/configuration", ({ response }) => {
                return response(200).json({});
            }),
            http.untyped.get("/api/webhooks", () => {
                return HttpResponse.json([]);
            }),
        );
    });

    function mountTarget(inputs = [{ name: "input", label: "input", type: "text", value: "value" }]) {
        return mount(FormTool, {
            propsData: {
                id: "input",
                datatypes: [],
                step: {
                    id: 0,
                    config_form: {
                        id: "tool_id+1.0",
                        name: "tool_name",
                        version: "1.0",
                        description: "description",
                        inputs,
                        help: "help_text",
                        help_format: "restructuredtext",
                        versions: ["1.0", "2.0", "3.0"],
                        citations: false,
                    },
                    outputs: [],
                    inputs: [],
                    post_job_actions: {},
                },
            },
            localVue,
            stubs: {
                ToolFooter: { template: "<div>tool-footer</div>" },
            },
            pinia: createTestingPinia({ createSpy: vi.fn }),
            provide: { workflowId: "mock-workflow" },
        });
    }

    it("changes between different versions", async () => {
        const wrapper = mountTarget();

        const dropdowns = wrapper.findAll(".tool-versions .dropdown-item");
        let version = dropdowns.at(1);
        expect(version.text()).toBe("Switch to 2.0");
        await version.trigger("click");

        let state = wrapper.emitted().onSetData[0][1];
        expect(state.tool_version).toEqual("2.0");
        expect(state.tool_id).toEqual("tool_id+2.0");

        version = dropdowns.at(0);
        expect(version.text()).toBe("Switch to 3.0");
        await version.trigger("click");

        state = wrapper.emitted().onSetData[1][1];
        expect(state.tool_version).toEqual("3.0");
        expect(state.tool_id).toEqual("tool_id+3.0");
        await flushPromises();
    });

    it("does not stamp UI metadata into a rules input payload", () => {
        const inputs = mountTarget([
            { name: "input", label: "input", type: "text", value: "value" },
            {
                name: "rules",
                label: "rules",
                type: "rules",
                value: {
                    mapping: [{ type: "list_identifiers", columns: [1] }],
                    rules: [{ type: "add_column_metadata", value: "identifier0" }],
                },
            },
        ]).vm.inputs;

        const rulesInput = inputs[1];
        const nestedEntries = [rulesInput.value.mapping[0], rulesInput.value.rules[0]];

        // Leak fixed: nested rule/mapping entries carry no UI-only keys.
        for (const entry of nestedEntries) {
            expect(entry).not.toHaveProperty("collapsible_value");
            expect(entry).not.toHaveProperty("connectable");
            expect(entry).not.toHaveProperty("is_workflow");
        }

        // #18741 preserved: the top-level rules input is runtime-editable / not connectable.
        expect(rulesInput.collapsible_value).toBeUndefined();
        expect(rulesInput.connectable).toBe(false);

        // Regression guard: sibling scalar inputs are still stamped as before.
        const textInput = inputs[0];
        expect(textInput.collapsible_value.__class__).toBe("RuntimeValue");
        expect(textInput.connectable).toBe(true);
    });
});
