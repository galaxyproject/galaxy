import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount, type Wrapper } from "@vue/test-utils";
import { PiniaVuePlugin } from "pinia";
import { afterEach, describe, expect, it, vi } from "vitest";
import type Vue from "vue";

import type { Step } from "@/stores/workflowStepStore";

import FormPickValue from "./FormPickValue.vue";
import FormElement from "@/components/Form/FormElement.vue";

const localVue = getLocalVue();
localVue.use(PiniaVuePlugin);

interface EmittedState {
    mode: string;
    num_inputs: number;
}

function makeStep(overrides: Partial<Step> = {}): Step {
    return {
        id: 0,
        name: "Pick Value",
        type: "pick_value",
        inputs: [],
        outputs: [{ name: "output", extensions: ["input"], optional: false }],
        input_connections: {},
        position: { left: 0, top: 0 },
        tool_state: { mode: "first_non_null", num_inputs: 2 },
        workflow_outputs: [],
        ...overrides,
    } as Step;
}

function mountPickValue(step?: Step): Wrapper<Vue> {
    return shallowMount(FormPickValue as any, {
        propsData: {
            step: step ?? makeStep(),
        },
        localVue,
        pinia: createTestingPinia({ createSpy: vi.fn }),
        provide: {
            workflowId: "mock-workflow",
        },
    });
}

function getLastEmittedState(wrapper: Wrapper<Vue>): EmittedState {
    const events = wrapper.emitted().onChange!;
    return events[events.length - 1]![0] as EmittedState;
}

function getEmittedCount(wrapper: Wrapper<Vue>): number {
    return wrapper.emitted().onChange!.length;
}

describe("FormPickValue", () => {
    afterEach(() => {
        vi.clearAllMocks();
    });

    describe("mode defaults", () => {
        it("defaults to first_non_null when tool_state is empty", () => {
            const wrapper = mountPickValue(makeStep({ tool_state: {} }));
            const state = getLastEmittedState(wrapper);
            expect(state.mode).toBe("first_non_null");
            expect(state.num_inputs).toBe(2);
        });

        it("preserves mode from tool_state", () => {
            const wrapper = mountPickValue(
                makeStep({
                    tool_state: { mode: "all_non_null", num_inputs: 3 },
                    input_connections: {
                        input_0: [{ id: 1, output_name: "output" }],
                        input_1: [{ id: 2, output_name: "output" }],
                        input_2: [{ id: 3, output_name: "output" }],
                    },
                }),
            );
            const state = getLastEmittedState(wrapper);
            expect(state.mode).toBe("all_non_null");
            expect(state.num_inputs).toBe(3);
        });
    });

    describe("mode changes", () => {
        it("emits onChange with updated mode", () => {
            const wrapper = mountPickValue();
            const formElement = wrapper.findComponent(FormElement);
            formElement.vm.$emit("input", "the_only_non_null");

            const state = getLastEmittedState(wrapper);
            expect(state.mode).toBe("the_only_non_null");
            expect(state.num_inputs).toBe(2);
        });

        it("preserves num_inputs when changing mode", () => {
            const wrapper = mountPickValue(makeStep({ tool_state: { mode: "first_non_null", num_inputs: 5 } }));
            const formElement = wrapper.findComponent(FormElement);
            formElement.vm.$emit("input", "all_non_null");

            const state = getLastEmittedState(wrapper);
            expect(state.mode).toBe("all_non_null");
            expect(state.num_inputs).toBe(5);
        });
    });

    describe("grow-on-connect", () => {
        it("increments num_inputs when last terminal gets connected", async () => {
            const step = makeStep({ tool_state: { mode: "first_non_null", num_inputs: 2 } });
            const wrapper = mountPickValue(step);

            // Simulate connecting to the last empty terminal (input_2, since num_inputs=2)
            await wrapper.setProps({
                step: {
                    ...step,
                    input_connections: {
                        input_0: [{ id: 1, output_name: "output" }],
                        input_1: [{ id: 2, output_name: "output" }],
                        input_2: [{ id: 3, output_name: "output" }],
                    },
                },
            });

            expect(getLastEmittedState(wrapper).num_inputs).toBe(3);
        });

        it("does not increment when a non-last terminal gets connected", async () => {
            const step = makeStep({
                tool_state: { mode: "first_non_null", num_inputs: 3 },
                input_connections: {
                    input_0: [{ id: 1, output_name: "output" }],
                    input_1: [{ id: 2, output_name: "output" }],
                },
            });
            const wrapper = mountPickValue(step);
            const countBefore = getEmittedCount(wrapper);

            // Connect to input_2 (not the last terminal input_3)
            await wrapper.setProps({
                step: {
                    ...step,
                    input_connections: {
                        input_0: [{ id: 1, output_name: "output" }],
                        input_1: [{ id: 2, output_name: "output" }],
                        input_2: [{ id: 3, output_name: "output" }],
                    },
                },
            });

            // num_inputs stays 3 since input_2 is not the last terminal (input_3)
            expect(getEmittedCount(wrapper)).toBe(countBefore);
        });
    });

    describe("shrink-on-disconnect", () => {
        it("decrements num_inputs when a connection is removed", async () => {
            const step = makeStep({
                tool_state: { mode: "first_non_null", num_inputs: 3 },
                input_connections: {
                    input_0: [{ id: 1, output_name: "output" }],
                    input_1: [{ id: 2, output_name: "output" }],
                    input_2: [{ id: 3, output_name: "output" }],
                },
            });
            const wrapper = mountPickValue(step);

            // Simulate disconnect of input_1 after compaction: input_2 renamed to input_1
            await wrapper.setProps({
                step: {
                    ...step,
                    input_connections: {
                        input_0: [{ id: 1, output_name: "output" }],
                        input_1: [{ id: 3, output_name: "output" }],
                    },
                },
            });

            expect(getLastEmittedState(wrapper).num_inputs).toBe(2);
        });

        it("does not shrink below minimum of 2", async () => {
            const step = makeStep({
                tool_state: { mode: "first_non_null", num_inputs: 2 },
                input_connections: {
                    input_0: [{ id: 1, output_name: "output" }],
                },
            });
            const wrapper = mountPickValue(step);

            // Disconnect all
            await wrapper.setProps({
                step: {
                    ...step,
                    input_connections: {},
                },
            });

            expect(getLastEmittedState(wrapper).num_inputs).toBe(2);
        });

        it("increases num_inputs on undo-of-shrink", async () => {
            const step = makeStep({
                tool_state: { mode: "first_non_null", num_inputs: 2 },
                input_connections: {
                    input_0: [{ id: 1, output_name: "output" }],
                },
            });
            const wrapper = mountPickValue(step);

            // Simulate undo restoring connections
            await wrapper.setProps({
                step: {
                    ...step,
                    tool_state: { mode: "first_non_null", num_inputs: 2 },
                    input_connections: {
                        input_0: [{ id: 1, output_name: "output" }],
                        input_1: [{ id: 2, output_name: "output" }],
                        input_2: [{ id: 3, output_name: "output" }],
                    },
                },
            });

            expect(getLastEmittedState(wrapper).num_inputs).toBe(3);
        });
    });

    describe("JSON-encoded tool_state", () => {
        it("handles JSON-string-encoded values from API", () => {
            // The build_module API may return tool_state values as JSON strings
            const wrapper = mountPickValue(
                makeStep({
                    tool_state: {
                        mode: JSON.stringify("the_only_non_null"),
                        num_inputs: JSON.stringify(4),
                    },
                    input_connections: {
                        input_0: [{ id: 1, output_name: "output" }],
                        input_1: [{ id: 2, output_name: "output" }],
                        input_2: [{ id: 3, output_name: "output" }],
                        input_3: [{ id: 4, output_name: "output" }],
                    },
                }),
            );
            const state = getLastEmittedState(wrapper);
            expect(state.mode).toBe("the_only_non_null");
            expect(state.num_inputs).toBe(4);
        });
    });
});
