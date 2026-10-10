import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { setupMockConfig } from "@tests/vitest/mockConfig";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import FormTool from "./FormTool.vue";
import FormDisplay from "@/components/Form/FormDisplay.vue";

vi.mock("@/api/schema", () => ({}));
setupMockConfig({ enable_tool_source_display: false });

const localVue = getLocalVue();

const { server, http } = useServerMock();

enableAutoUnmount(afterEach);

function textInput() {
    return { name: "input", label: "input", type: "text", value: "value" };
}

function rulesInput() {
    return {
        name: "rules",
        label: "rules",
        type: "rules",
        value: {
            mapping: [{ type: "list_identifiers", columns: [1] }],
            rules: [{ type: "add_column_metadata", value: "identifier0" }],
        },
    };
}

async function mountFormTool(inputs = [textInput()]) {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    const wrapper = mount(FormTool, {
        props: {
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
        global: { ...withPlugins(localVue, pinia), provide: { workflowId: "mock-workflow" } },
        stubs: {
            ToolFooter: { template: "<div>tool-footer</div>" },
        },
    });
    await flushPromises();
    return wrapper;
}

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

    it("emits the picked version's tool id and version when switching versions", async () => {
        const wrapper = await mountFormTool();

        const versionItems = wrapper.findAll(".tool-versions .dropdown-item");
        expect(versionItems.map((item) => item.text())).toEqual(["Switch to 3.0", "Switch to 2.0", "Selected 1.0"]);
        const [switchTo3, switchTo2] = versionItems;

        await switchTo2.trigger("click");
        expect(wrapper.emitted("onSetData")[0][1]).toMatchObject({ tool_version: "2.0", tool_id: "tool_id+2.0" });

        await switchTo3.trigger("click");
        expect(wrapper.emitted("onSetData")[1][1]).toMatchObject({ tool_version: "3.0", tool_id: "tool_id+3.0" });
    });

    describe("with a rules input", () => {
        async function mountedInputs() {
            const wrapper = await mountFormTool([textInput(), rulesInput()]);
            const [text, rules] = wrapper.findComponent(FormDisplay).props("inputs");
            return { text, rules };
        }

        it("keeps UI-only metadata out of its nested mapping and rule entries", async () => {
            const { rules } = await mountedInputs();

            for (const entry of [rules.value.mapping[0], rules.value.rules[0]]) {
                expect(entry).not.toHaveProperty("collapsible_value");
                expect(entry).not.toHaveProperty("connectable");
                expect(entry).not.toHaveProperty("is_workflow");
            }
        });

        it("leaves the rules input runtime-editable and not connectable", async () => {
            const { rules } = await mountedInputs();

            expect(rules.collapsible_value).toBeUndefined();
            expect(rules.connectable).toBe(false);
        });

        it("still marks a sibling text input as a connectable runtime value", async () => {
            const { text } = await mountedInputs();

            expect(text.collapsible_value.__class__).toBe("RuntimeValue");
            expect(text.connectable).toBe(true);
        });
    });
});
