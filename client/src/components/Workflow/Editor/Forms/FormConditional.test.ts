import "@/composables/__mocks__/filter";

import { getLocalVue } from "@tests/vitest/helpers";
import { mount, shallowMount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, PiniaVuePlugin, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type Vue from "vue";

import { type Step, type Steps, useWorkflowStepStore } from "@/stores/workflowStepStore";

import FormConditional from "./FormConditional.vue";
import FormElement from "@/components/Form/FormElement.vue";

const { confirmMock } = vi.hoisted(() => ({ confirmMock: vi.fn() }));

vi.mock("@/composables/confirmDialog", () => ({
    useConfirmDialog: () => ({ confirm: confirmMock }),
}));

const localVue = getLocalVue();
localVue.use(PiniaVuePlugin);

const bootstrappedVue = getLocalVue(true);
bootstrappedVue.use(PiniaVuePlugin);

const GATED_STEP_ID = 3;

function makeSteps(gatedStepOverrides: Partial<Step> = {}): Steps {
    const dataInput = (id: number, optional: boolean) =>
        ({
            id,
            type: "data_input",
            name: "Input dataset",
            inputs: [],
            outputs: [{ name: "output", extensions: ["input"], optional }],
            input_connections: {},
            position: { left: 0, top: 0 },
            tool_state: {},
            workflow_outputs: [],
        }) as unknown as Step;

    return {
        1: dataInput(1, true),
        2: dataInput(2, false),
        3: {
            id: GATED_STEP_ID,
            type: "tool",
            name: "Concatenate datasets",
            inputs: [
                {
                    name: "input1",
                    label: "First input",
                    multiple: false,
                    extensions: ["txt"],
                    optional: false,
                    input_type: "dataset",
                },
                {
                    name: "cond|input2",
                    label: "Second input",
                    multiple: false,
                    extensions: ["txt"],
                    optional: false,
                    input_type: "dataset",
                },
                {
                    name: "queries_0|input3",
                    label: "Repeat input",
                    multiple: false,
                    extensions: ["txt"],
                    optional: false,
                    input_type: "dataset",
                },
                {
                    name: "input4",
                    label: "Always present input",
                    multiple: false,
                    extensions: ["txt"],
                    optional: false,
                    input_type: "dataset",
                },
            ],
            outputs: [{ name: "out_file1", extensions: ["txt"], optional: false }],
            input_connections: {
                input1: { id: 1, output_name: "output" },
                "cond|input2": { id: 1, output_name: "output" },
                "queries_0|input3": { id: 1, output_name: "output" },
                input4: { id: 2, output_name: "output" },
            },
            position: { left: 0, top: 0 },
            tool_state: {
                input1: '{"__class__": "ConnectedValue"}',
                cond: { input2: { __class__: "ConnectedValue" } },
                queries: '[{"__index__": 0, "input3": {"__class__": "ConnectedValue"}}]',
            },
            workflow_outputs: [],
            ...gatedStepOverrides,
        } as unknown as Step,
    } as unknown as Steps;
}

function mountWith(
    mountFn: typeof mount | typeof shallowMount,
    vue: typeof localVue,
    gatedStepOverrides: Partial<Step>,
): Wrapper<Vue> {
    const pinia = createPinia();
    setActivePinia(pinia);
    const stepStore = useWorkflowStepStore("mock-workflow");
    const steps = makeSteps(gatedStepOverrides);
    Object.values(steps).forEach((step) => stepStore.addStep(step, false, false));

    return mountFn(FormConditional as any, {
        propsData: { step: steps[GATED_STEP_ID] },
        localVue: vue,
        pinia,
        provide: { workflowId: "mock-workflow" },
    });
}

function mountConditional(gatedStepOverrides: Partial<Step> = {}): Wrapper<Vue> {
    return mountWith(shallowMount, localVue, gatedStepOverrides);
}

/** Renders the real form elements, so a control this form cannot mount is a failure. */
function mountConditionalDeep(gatedStepOverrides: Partial<Step> = {}): Wrapper<Vue> {
    return mountWith(mount, bootstrappedVue, gatedStepOverrides);
}

function modeElement(wrapper: Wrapper<Vue>) {
    return wrapper.findAllComponents(FormElement).at(0);
}

/** `options` reaches FormElement through attrs rather than a declared prop. */
function optionValues(wrapper: Wrapper<Vue>, index: number): string[] {
    return optionPairs(wrapper, index).map((option) => option[1]!);
}

function optionPairs(wrapper: Wrapper<Vue>, index: number): string[][] {
    return wrapper.findAllComponents(FormElement).at(index).vm.$attrs["options"] as unknown as string[][];
}

function updates(wrapper: Wrapper<Vue>): Array<[number, Partial<Step>]> {
    return (wrapper.emitted().onUpdateStep ?? []) as Array<[number, Partial<Step>]>;
}

function lastUpdate(wrapper: Wrapper<Vue>): Partial<Step> {
    const emitted = updates(wrapper);
    return emitted[emitted.length - 1]![1];
}

describe("FormConditional", () => {
    beforeEach(() => {
        confirmMock.mockReset();
    });

    describe("rendering", () => {
        it("mounts the mode control as a select showing the current mode", () => {
            const wrapper = mountConditionalDeep();
            const select = wrapper.find("#__conditional");
            expect(select.find(".multiselect").exists()).toBe(true);
            expect(select.text()).toContain("Always run this step");
        });

        it("mounts the gated-input control as a select showing the gated input", () => {
            const wrapper = mountConditionalDeep({ when: "$(inputs.input1 !== null)" });
            const select = wrapper.find("#__when_input");
            expect(select.find(".multiselect").exists()).toBe(true);
            expect(select.text()).toContain("First input");
        });
    });

    describe("mode round-trips", () => {
        it("reads an ungated step as unconditional", () => {
            const wrapper = mountConditional();
            expect(modeElement(wrapper).props("value")).toBe("none");
        });

        it("reads the boolean gate", () => {
            const wrapper = mountConditional({ when: "$(inputs.when)" });
            expect(modeElement(wrapper).props("value")).toBe("boolean");
        });

        it("reads a generated presence gate and the input it addresses", () => {
            const wrapper = mountConditional({ when: "$(inputs.input1 !== null)" });
            expect(modeElement(wrapper).props("value")).toBe("presence");
            expect(wrapper.findAllComponents(FormElement).at(1).props("value")).toBe("input1");
        });

        it("reads a nested presence gate", () => {
            const wrapper = mountConditional({
                when: "$(inputs.cond.input2 !== null)",
            });
            expect(modeElement(wrapper).props("value")).toBe("presence");
            expect(wrapper.findAllComponents(FormElement).at(1).props("value")).toBe("cond|input2");
        });

        it("reads a repeat presence gate", () => {
            const wrapper = mountConditional({ when: "$(inputs.queries[0].input3 !== null)" });
            expect(modeElement(wrapper).props("value")).toBe("presence");
            expect(wrapper.findAllComponents(FormElement).at(1).props("value")).toBe("queries_0|input3");
        });

        it("reads anything else as a custom expression", () => {
            const wrapper = mountConditional({ when: "$(inputs.input1 != null)" });
            expect(modeElement(wrapper).props("value")).toBe("custom");
        });
    });

    describe("gateable inputs", () => {
        it("offers only connections whose source can be absent", () => {
            const wrapper = mountConditional();
            expect(optionValues(wrapper, 0)).toContain("presence");

            const gated = mountConditional({ when: "$(inputs.input1 !== null)" });
            expect(optionPairs(gated, 1).map((option) => option[1])).not.toContain("input4");
        });

        it("does not offer the presence mode when nothing gateable is connected", () => {
            const wrapper = mountConditional({
                input_connections: { input4: { id: 2, output_name: "output" } },
            });
            expect(optionValues(wrapper, 0)).not.toContain("presence");
        });
    });

    describe("nested gate inputs", () => {
        it("offers an input nested in a repeat", () => {
            const gated = mountConditional({ when: "$(inputs.input1 !== null)" });
            expect(optionPairs(gated, 1).map((option) => option[1])).toContain("queries_0|input3");
        });

        it("offers an input nested in a conditional", () => {
            const gated = mountConditional({ when: "$(inputs.input1 !== null)" });
            expect(optionPairs(gated, 1).map((option) => option[1])).toContain("cond|input2");
        });
    });

    describe("writing a gate", () => {
        it("writes the boolean gate and clears its connection", () => {
            const wrapper = mountConditional();
            modeElement(wrapper).vm.$emit("input", "boolean");
            expect(lastUpdate(wrapper).when).toBe("$(inputs.when)");
            expect(lastUpdate(wrapper).input_connections).toHaveProperty("when", undefined);
        });

        it("writes a presence gate for the first gateable input", () => {
            const wrapper = mountConditional();
            modeElement(wrapper).vm.$emit("input", "presence");
            expect(lastUpdate(wrapper).when).toBe("$(inputs.input1 !== null)");
        });

        it("rewrites the expression when the gated input changes", () => {
            const wrapper = mountConditional({ when: "$(inputs.input1 !== null)" });
            wrapper.findAllComponents(FormElement).at(1).vm.$emit("input", "cond|input2");
            expect(lastUpdate(wrapper).when).toBe("$(inputs.cond.input2 !== null)");
        });

        it("writes an indexed presence gate for a repeat input", () => {
            const wrapper = mountConditional({ when: "$(inputs.input1 !== null)" });
            wrapper.findAllComponents(FormElement).at(1).vm.$emit("input", "queries_0|input3");
            expect(lastUpdate(wrapper).when).toBe("$(inputs.queries[0].input3 !== null)");
        });

        it("ignores a selection of the mode already in effect", () => {
            const wrapper = mountConditional({ when: "$(inputs.when)" });
            modeElement(wrapper).vm.$emit("input", "boolean");
            expect(updates(wrapper)).toHaveLength(0);
        });
    });

    describe("clearing a gate", () => {
        it("clears a generated gate without asking", async () => {
            const wrapper = mountConditional({ when: "$(inputs.input1 !== null)" });
            modeElement(wrapper).vm.$emit("input", "none");
            await flushPromises();
            expect(confirmMock).not.toHaveBeenCalled();
            expect(lastUpdate(wrapper).when).toBeUndefined();
        });

        it("asks before clearing a hand-written expression", async () => {
            confirmMock.mockResolvedValue(true);
            const wrapper = mountConditional({ when: "$(inputs.input1 != null)" });
            modeElement(wrapper).vm.$emit("input", "none");
            await flushPromises();
            expect(confirmMock).toHaveBeenCalled();
            expect(lastUpdate(wrapper).when).toBeUndefined();
        });

        it("keeps a hand-written expression when the user declines", async () => {
            confirmMock.mockResolvedValue(false);
            const wrapper = mountConditional({ when: "$(inputs.input1 != null)" });
            modeElement(wrapper).vm.$emit("input", "none");
            await flushPromises();
            expect(confirmMock).toHaveBeenCalled();
            expect(updates(wrapper)).toHaveLength(0);
        });

        it("asks before replacing a hand-written expression with the boolean gate", async () => {
            confirmMock.mockResolvedValue(false);
            const wrapper = mountConditional({ when: "$(inputs.flag && inputs.other !== null)" });
            modeElement(wrapper).vm.$emit("input", "boolean");
            await flushPromises();
            expect(confirmMock).toHaveBeenCalled();
            expect(updates(wrapper)).toHaveLength(0);
        });

        it("asks before replacing a hand-written expression with a presence gate", async () => {
            confirmMock.mockResolvedValue(false);
            const wrapper = mountConditional({ when: "$(inputs.flag && inputs.other !== null)" });
            modeElement(wrapper).vm.$emit("input", "presence");
            await flushPromises();
            expect(confirmMock).toHaveBeenCalled();
            expect(updates(wrapper)).toHaveLength(0);
        });

        it("replaces a hand-written expression once the user agrees", async () => {
            confirmMock.mockResolvedValue(true);
            const wrapper = mountConditional({ when: "$(inputs.flag && inputs.other !== null)" });
            modeElement(wrapper).vm.$emit("input", "boolean");
            await flushPromises();
            expect(lastUpdate(wrapper).when).toBe("$(inputs.when)");
        });

        it("does not ask when the expression is one this form generated", async () => {
            const wrapper = mountConditional({ when: "$(inputs.input1 !== null)" });
            modeElement(wrapper).vm.$emit("input", "boolean");
            await flushPromises();
            expect(confirmMock).not.toHaveBeenCalled();
            expect(lastUpdate(wrapper).when).toBe("$(inputs.when)");
        });

        it("shows a hand-written expression without rewriting it", () => {
            const expression = "$(inputs.input1 != null && inputs.other)";
            const wrapper = mountConditional({ when: expression });
            const custom = wrapper.findAllComponents(FormElement).at(1);
            expect(custom.props("value")).toBe(expression);
            expect(custom.props("disabled")).toBe(true);
            expect(updates(wrapper)).toHaveLength(0);
        });
    });
});
