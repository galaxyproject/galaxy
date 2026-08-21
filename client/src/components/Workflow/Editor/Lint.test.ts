import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import { PiniaVuePlugin, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import { type Steps, useWorkflowStepStore } from "@/stores/workflowStepStore";

import { useLintData } from "./modules/useLinting";
import lintStepsData from "./test-data/lint_steps.json";

import Lint from "./Lint.vue";

const localVue = getLocalVue();
localVue.use(PiniaVuePlugin);

const steps: Steps = lintStepsData as unknown as Steps;
const stepsRef = ref(steps);

describe("Lint", () => {
    let wrapper: Wrapper<Vue>;
    let stepStore: ReturnType<typeof useWorkflowStepStore>;

    beforeEach(() => {
        const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
        setActivePinia(pinia);

        wrapper = mount(Lint as object, {
            propsData: {
                lintData: useLintData(
                    ref("1"),
                    stepsRef,
                    ref(testDatatypesMapper),
                    ref("workflow annotation"),
                    ref(null),
                    ref("MIT"),
                    ref([
                        {
                            class: "Person",
                            name: "Test Creator",
                        },
                    ]),
                ),
                steps: steps,
                datatypesMapper: testDatatypesMapper,
                hasChanges: false,
            },
            localVue,
            pinia,
            provide: { workflowId: "mock-workflow" },
        });

        stepStore = useWorkflowStepStore("mock-workflow");
        Object.values(steps).map((step) => stepStore.addStep(step));
    });

    it("test checked vs unchecked issues", async () => {
        /** Passing: 4
         * - Critical: Has unique labels;
         * - Non-critical: Has annotation, creator and license
         */
        const numLintChecksPassing = 4;
        const checked = wrapper.findAll("[data-description='lint okay section']");
        expect(checked.length).toBe(numLintChecksPassing);

        /** Failing: 5
         * - Critical: untypedParameters, disconnectedInputs, missingMetadata, unlabeledOutputs
         * - Non-critical: No readme
         */
        const numLintChecksFailing = 5;
        const unchecked = wrapper.findAll("[data-description='lint warning section']");
        expect(unchecked.length).toBe(numLintChecksFailing);

        const links = wrapper.findAll("[data-description='autofix item link']");
        // Only the autofix-able issues have links
        expect(links.length).toBeGreaterThanOrEqual(4);

        // Check the order of warnings as they appear in the rendered output
        expect(links.at(0).text().toLowerCase()).toContain("untyped_parameter");
        expect(links.at(1).text().toLowerCase()).toContain("step label: input_label");
        expect(links.at(2).text().toLowerCase()).toContain("data input: missing an annotation");
        expect(links.at(3).text().toLowerCase()).toContain("step label: output");

        // Only 1 non-critical, attribute-related issue
        const attributeLink = wrapper.findAll("[data-description='attribute link']");
        expect(attributeLink.length).toBe(1);
        expect(attributeLink.at(0).text().toLowerCase()).toContain("provide readme for your workflow");
    });

    it("should fire refactor event to extract untyped parameter and remove unlabeled workflows", async () => {
        const autoFixButton = wrapper.find("[data-description='auto fix lint issues']");
        expect(autoFixButton.exists()).toBe(true);
        await autoFixButton.trigger("click");
        expect(wrapper.emitted().onRefactor?.length).toBe(1);
        const actions = wrapper.emitted().onRefactor![0]![0];
        expect(actions.length).toBe(3);
        expect(actions[0].action_type).toBe("extract_untyped_parameter");
        expect(actions[0].name).toBe("untyped_parameter");
        expect(actions[1].action_type).toBe("extract_input");
        expect(actions[2].action_type).toBe("remove_unlabeled_workflow_outputs");
    });

    it("should include connect input action when input disconnected", async () => {
        stepStore.removeStep(0);
        await wrapper.vm.$nextTick();
        const autoFixButton = wrapper.find("[data-description='auto fix lint issues']");
        expect(autoFixButton.exists()).toBe(true);
        await autoFixButton.trigger("click");
        expect(wrapper.emitted().onRefactor?.length).toBe(1);
        const actions = wrapper.emitted().onRefactor![0]![0];
        expect(actions.length).toBe(3);
        expect(actions[0].action_type).toBe("extract_untyped_parameter");
        expect(actions[0].name).toBe("untyped_parameter");
        expect(actions[1].action_type).toBe("extract_input");
        expect(actions[2].action_type).toBe("remove_unlabeled_workflow_outputs");
    });
});

describe("Lint conditional gates", () => {
    function mountLint(when: string | undefined, inputConnections: Record<string, unknown>): Wrapper<Vue> {
        const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
        setActivePinia(pinia);

        const gatedSteps = {
            ...(JSON.parse(JSON.stringify(steps)) as Steps),
            3: {
                id: 3,
                name: "Concatenate datasets",
                label: "gated",
                type: "tool",
                content_id: "cat1",
                inputs: [],
                outputs: [],
                input_connections: inputConnections,
                position: { left: 0, top: 0 },
                tool_state: {},
                workflow_outputs: [],
                when,
            },
        } as unknown as Steps;
        const gatedStepsRef = ref(gatedSteps);

        const wrapper = mount(Lint as object, {
            propsData: {
                lintData: useLintData(ref("1"), gatedStepsRef, ref(testDatatypesMapper)),
                steps: gatedSteps,
                datatypesMapper: testDatatypesMapper,
                hasChanges: false,
            },
            localVue,
            pinia,
            provide: { workflowId: "mock-workflow" },
        });

        const stepStore = useWorkflowStepStore("mock-workflow");
        Object.values(gatedSteps).map((step) => stepStore.addStep(step));
        return wrapper;
    }

    function sectionStatus(wrapper: Wrapper<Vue>): string | void {
        return wrapper.find("[data-description='linting conditional gates']").attributes("data-lint-status");
    }

    it("says nothing when no step is gated", () => {
        const wrapper = mountLint(undefined, {});
        expect(wrapper.find("[data-description='linting conditional gates']").exists()).toBe(false);
    });

    it("passes when a gate reads a connected input", () => {
        const wrapper = mountLint("$(inputs.when)", { when: { id: 0, output_name: "output" } });
        expect(sectionStatus(wrapper)).toBe("ok");
    });

    it("warns when a gate reads an input nothing is connected to", () => {
        const wrapper = mountLint("$(inputs.when)", {});
        expect(sectionStatus(wrapper)).toBe("warning");
        expect(wrapper.find("[data-description='linting conditional gates']").text()).toContain("when");
    });
});
