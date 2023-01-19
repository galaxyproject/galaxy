import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import NodeOutput from "./NodeOutput.vue";
import { createPinia, setActivePinia } from "pinia";
import { useWorkflowStepStore, type Step, type Steps } from "@/stores/workflowStepStore";
import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import { mockOffset, advancedSteps } from "./test_fixtures";
import { nextTick, ref } from "vue";
import { terminalFactory } from "./modules/terminals";

const localVue = getLocalVue();

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
    };
}

function stepForLabel(label: string, steps: Steps) {
    const step = Object.values(steps).find((step) => step.label === label);
    if (!step) {
        throw "step not found for test";
    }
    return step;
}

const transform = ref({ x: 0, y: 0, k: 1 });

describe("NodeOutput", () => {
    let pinia: ReturnType<typeof createPinia>;
    let stepStore: ReturnType<typeof useWorkflowStepStore>;

    beforeEach(() => {
        pinia = createPinia();
        setActivePinia(pinia);
        stepStore = useWorkflowStepStore();
        Object.values(advancedSteps).map((step) => stepStore.addStep(step));
    });

    it("does not display multiple icon if not mapped over", async () => {
        const simpleDataStep = stepForLabel("simple data", stepStore.steps);
        const propsData = propsForStep(simpleDataStep);
        const wrapper = shallowMount(NodeOutput, {
            propsData: propsData,
            localVue,
            pinia,
            provide: { transform },
        });
        expect(wrapper.find(".multiple").exists()).toBe(false);
    });
    it("displays multiple icon if not mapped over", async () => {
        const simpleDataStep = stepForLabel("simple data", stepStore.steps);
        const listInputStep = stepForLabel("list input", stepStore.steps);
        const inputTerminal = terminalFactory(simpleDataStep.id, simpleDataStep.inputs[0]!, testDatatypesMapper);
        const outputTerminal = terminalFactory(listInputStep.id, listInputStep.outputs[0]!, testDatatypesMapper);
        const propsData = propsForStep(simpleDataStep);
        const wrapper = shallowMount(NodeOutput, {
            propsData: propsData,
            localVue,
            pinia,
            provide: { transform },
        });
        expect(wrapper.find(".multiple").exists()).toBe(false);
        inputTerminal.connect(outputTerminal);
        await nextTick();
        expect(wrapper.find(".multiple").exists()).toBe(true);
        inputTerminal.disconnect(outputTerminal);
        await nextTick();
        expect(wrapper.find(".multiple").exists()).toBe(false);
    });
});
