import { shallowMount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";
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
    observe = jest.fn();
    unobserve = jest.fn();
    disconnect = jest.fn();
}

// eslint-disable-next-line compat/compat
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
            propsData: propsData,
            localVue,
            pinia,
            provide: { transform, workflowId: "mock-workflow" },
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
            propsData: propsData,
            localVue,
            pinia,
            provide: { transform, workflowId: "mock-workflow" },
        });
        expect(wrapper.find(".mapped-over").exists()).toBe(false);
        inputTerminal.connect(outputTerminal);
        await nextTick();
        expect(wrapper.find(".mapped-over").exists()).toBe(true);
        inputTerminal.disconnect(outputTerminal);
        await nextTick();
        expect(wrapper.find(".mapped-over").exists()).toBe(false);
    });
});
