import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick, ref } from "vue";

import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import { type UndoRedoStore, useUndoRedoStore } from "@/stores/undoRedoStore";
import { useConnectionStore } from "@/stores/workflowConnectionStore";
import { type Step, type Steps, useWorkflowStepStore } from "@/stores/workflowStepStore";

import { terminalFactory } from "./modules/terminals";
import { advancedSteps, mockOffset } from "./test_fixtures";

import NodeOutput from "./NodeOutput.vue";

const localVue = getLocalVue();

class ResizeObserver {
    observe = vi.fn();
    unobserve = vi.fn();
    disconnect = vi.fn();
}

window.ResizeObserver = ResizeObserver;

function propsForStep(step: Step) {
    return {
        output: step.outputs[0],
        workflowOutputs: [],
        stepType: step.type,
        stepId: step.id,
        postJobActions: step.post_job_actions,
        stepPosition: step.position,
        rootOffset: mockOffset,
        parentOffset: mockOffset,
        scroll: { x: ref(0), y: ref(0) },
        scale: 1,
        datatypesMapper: testDatatypesMapper,
        parentNode: null,
        readonly: true,
        blank: false,
    };
}

function stepForLabel(label: string, steps: Steps) {
    const step = Object.values(steps).find((step) => step.label === label);
    if (!step) {
        throw Error("step not found for test");
    }
    return step;
}

const transform = ref({ x: 0, y: 0, k: 1 });

describe("NodeOutput", () => {
    let pinia: ReturnType<typeof createPinia>;
    let stepStore: ReturnType<typeof useWorkflowStepStore>;
    let connectionStore: ReturnType<typeof useConnectionStore>;
    let undoRedoStore: UndoRedoStore;

    beforeEach(() => {
        pinia = createPinia();
        setActivePinia(pinia);
        stepStore = useWorkflowStepStore("mock-workflow");
        connectionStore = useConnectionStore("mock-workflow");
        undoRedoStore = useUndoRedoStore("mock-workflow");
        Object.values(advancedSteps).map((step) => stepStore.addStep(step));
    });

    it("does not display multiple icon if not mapped over", async () => {
        const simpleDataStep = stepForLabel("simple data", stepStore.steps);
        const propsData = propsForStep(simpleDataStep);
        const wrapper = shallowMount(NodeOutput as any, {
            props: propsData,
            global: { ...localVue, provide: { transform, workflowId: "mock-workflow" } },
            pinia,
        });
        expect(wrapper.find(".multiple").exists()).toBe(false);
    });

    it("displays multiple icon if not mapped over", async () => {
        const simpleDataStep = stepForLabel("simple data", stepStore.steps);
        const listInputStep = stepForLabel("list input", stepStore.steps);
        const inputTerminal = terminalFactory(simpleDataStep.id, simpleDataStep.inputs[0]!, testDatatypesMapper, {
            connectionStore,
            stepStore,
            undoRedoStore,
        } as any);
        const outputTerminal = terminalFactory(listInputStep.id, listInputStep.outputs[0]!, testDatatypesMapper, {
            connectionStore,
            stepStore,
            undoRedoStore,
        } as any);
        const propsData = propsForStep(simpleDataStep);
        const wrapper = shallowMount(NodeOutput as any, {
            props: propsData,
            global: { ...localVue, provide: { transform, workflowId: "mock-workflow" } },
            pinia,
        });
        expect(wrapper.find(".mapped-over").exists()).toBe(false);
        inputTerminal.connect(outputTerminal);
        await nextTick();
        expect(wrapper.find(".mapped-over").exists()).toBe(true);
        inputTerminal.disconnect(outputTerminal);
        await nextTick();
        expect(wrapper.find(".mapped-over").exists()).toBe(false);
    });

    function mountWithOutputLabels(firstLabel: string, secondLabel: string) {
        const simpleDataStep = stepForLabel("simple data", stepStore.steps);
        const listInputStep = stepForLabel("list input", stepStore.steps);
        const workflowOutputs = [{ output_name: simpleDataStep.outputs[0]!.name, label: firstLabel }];
        stepStore.updateStep({ ...simpleDataStep, workflow_outputs: workflowOutputs });
        stepStore.updateStep({
            ...listInputStep,
            workflow_outputs: [{ output_name: listInputStep.outputs[0]!.name, label: secondLabel }],
        });
        return shallowMount(NodeOutput as any, {
            props: { ...propsForStep(simpleDataStep), workflowOutputs },
            global: { ...localVue, provide: { transform, workflowId: "mock-workflow" } },
            pinia,
        });
    }

    // v-g-tooltip refuses to show on any element with a disabled attribute, so a duplicate
    // label must drop the attribute entirely rather than render disabled="false".
    it("leaves the label tooltip enabled when the output label is a duplicate", async () => {
        const wrapper = mountWithOutputLabels("same label", "same label");
        const labelSpan = wrapper.find("span.alert-danger");
        expect(labelSpan.exists()).toBe(true);
        expect(labelSpan.attributes("disabled")).toBeUndefined();
    });

    it("disables the label tooltip when the output label is unique", async () => {
        const wrapper = mountWithOutputLabels("first label", "second label");
        const labelSpan = wrapper.find("span[title]");
        expect(labelSpan.text()).toBe("first label");
        expect(labelSpan.attributes("disabled")).toBeDefined();
    });
});
