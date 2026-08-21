import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount, type Wrapper } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type Vue from "vue";
import type { VueConstructor } from "vue";
import { nextTick, ref } from "vue";

import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import type { useWorkflowStores } from "@/composables/workflowStores";
import { useUndoRedoStore } from "@/stores/undoRedoStore";
import { useConnectionStore } from "@/stores/workflowConnectionStore";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { type Step, type Steps, useWorkflowStepStore } from "@/stores/workflowStepStore";

import { type OutputTerminals, terminalFactory } from "./modules/terminals";
import { advancedSteps, mockOffset } from "./test_fixtures";

import NodeInput from "./NodeInput.vue";

const localVue = getLocalVue();
const workflowId = "node-input-drop-preview";
const transform = ref({ x: 0, y: 0, k: 1 });

class ResizeObserver {
    observe = vi.fn();
    unobserve = vi.fn();
    disconnect = vi.fn();
}

// eslint-disable-next-line compat/compat
window.ResizeObserver = ResizeObserver;

function stepForLabel(label: string, steps: Steps): Step {
    const step = Object.values(steps).find((step) => step.label === label);
    if (!step) {
        throw new Error(`No step labeled '${label}'`);
    }
    return step;
}

describe("NodeInput drop preview", () => {
    let pinia: ReturnType<typeof createPinia>;
    let steps: Steps;

    beforeEach(() => {
        pinia = createPinia();
        setActivePinia(pinia);
        const stepStore = useWorkflowStepStore(workflowId);
        steps = JSON.parse(JSON.stringify(advancedSteps)) as Steps;
        Object.values(steps).forEach((step) => stepStore.addStep(step));
    });

    function outputTerminal(stepLabel: string): OutputTerminals {
        const step = stepForLabel(stepLabel, steps);
        return terminalFactory(step.id, step.outputs[0]!, testDatatypesMapper, {
            connectionStore: useConnectionStore(workflowId),
            stepStore: useWorkflowStepStore(workflowId),
            undoRedoStore: useUndoRedoStore(workflowId),
        } as unknown as ReturnType<typeof useWorkflowStores>) as OutputTerminals;
    }

    function addReceiverStep(label: string, type: Step["type"]): void {
        const template = stepForLabel("simple data", steps);
        const id = Math.max(...Object.values(steps).map((step) => step.id)) + 1;
        const step = {
            ...JSON.parse(JSON.stringify(template)),
            id,
            type,
            label,
            name: label,
            input_connections: {},
        } as Step;
        steps[id] = step;
        useWorkflowStepStore(workflowId).addStep(step);
    }

    function mountInput(stepLabel: string): Wrapper<Vue> {
        const step = stepForLabel(stepLabel, steps);
        return shallowMount(NodeInput as unknown as VueConstructor<Vue>, {
            propsData: {
                input: step.inputs[0],
                stepId: step.id,
                datatypesMapper: testDatatypesMapper,
                stepPosition: step.position,
                rootOffset: mockOffset,
                scale: 1,
                scroll: { x: ref(0), y: ref(0) },
                parentNode: null,
                readonly: false,
                blank: false,
            },
            localVue,
            pinia,
            provide: { transform, workflowId, isDragging: ref(true) },
        });
    }

    async function preview(outputStepLabel: string, inputStepLabel: string) {
        useWorkflowStateStore(workflowId).draggingTerminal = outputTerminal(outputStepLabel);
        const wrapper = mountInput(inputStepLabel);
        await nextTick();
        return wrapper;
    }

    it("shows a directly accepted drop in green", async () => {
        const wrapper = await preview("data input", "simple data");

        expect(wrapper.find(".input-terminal").classes()).toContain("can-accept");
        expect(wrapper.find(".input-terminal").classes()).not.toContain("can-not-accept");
    });

    it("shows a presence-gated drop in green with an actionable explanation", async () => {
        const wrapper = await preview("optional data input", "simple data");

        expect(wrapper.find(".input-terminal").classes()).toContain("can-accept");
        expect(wrapper.find(".input-terminal").classes()).not.toContain("can-not-accept");
        expect(wrapper.text()).toContain("Drop to connect and run this step only when From is provided.");
        expect(wrapper.text()).not.toContain("Cannot connect an optional output");
    });

    it("offers presence gating for a required subworkflow input", async () => {
        addReceiverStep("required subworkflow", "subworkflow");

        const wrapper = await preview("optional data input", "required subworkflow");

        expect(wrapper.find(".input-terminal").classes()).toContain("can-accept");
        expect(wrapper.find(".input-terminal").classes()).not.toContain("can-not-accept");
        expect(wrapper.text()).toContain("Drop to connect and run this step only when From is provided.");
    });

    it("does not offer presence gating for a pause step", async () => {
        addReceiverStep("pause for review", "pause");

        const wrapper = await preview("optional data input", "pause for review");

        expect(wrapper.find(".input-terminal").classes()).toContain("can-not-accept");
        expect(wrapper.find(".input-terminal").classes()).not.toContain("can-accept");
        expect(wrapper.text()).toContain("Cannot connect an optional output to a non-optional input");
        expect(wrapper.text()).not.toContain("run this step only when");
    });

    it("keeps a genuinely incompatible drop orange with its rejection", async () => {
        const wrapper = await preview("optional data input", "list collection input");

        expect(wrapper.find(".input-terminal").classes()).toContain("can-not-accept");
        expect(wrapper.find(".input-terminal").classes()).not.toContain("can-accept");
        expect(wrapper.text()).toContain("Cannot attach a data output to a collection input.");
    });
});
