import { createTestingPinia } from "@pinia/testing";
import { runInTestScope } from "@tests/vitest/effectScope";
import { emittedArg, getLocalVue, nth, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount, type VueWrapper } from "@vue/test-utils";
import { setActivePinia } from "pinia";
import { afterEach, describe, expect, it, vi } from "vitest";
import { nextTick, ref } from "vue";

import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import { type Steps, useWorkflowStepStore } from "@/stores/workflowStepStore";

import { useLintData } from "./modules/useLinting";
import lintStepsData from "./test-data/lint_steps.json";

import Lint from "./Lint.vue";

enableAutoUnmount(afterEach);

function mountLint() {
    // The historical fixture deliberately includes incomplete workflow steps.
    const steps = structuredClone(lintStepsData) as unknown as Steps;
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    setActivePinia(pinia);
    const lintData = runInTestScope(() =>
        useLintData(
            ref("1"),
            ref(steps),
            ref(testDatatypesMapper),
            ref("workflow annotation"),
            ref(null),
            ref("MIT"),
            ref([{ class: "Person", name: "Test Creator" }]),
        ),
    );
    const wrapper = mount(Lint, {
        props: { lintData, steps, hasChanges: false },
        global: { ...withPlugins(getLocalVue(), pinia), provide: { workflowId: "mock-workflow" } },
    });
    const stepStore = useWorkflowStepStore("mock-workflow");
    Object.values(steps).forEach((step) => stepStore.addStep(step));
    return { wrapper, stepStore };
}

describe("Lint", () => {
    it("shows four passing checks, five warnings, and the warning links in order", async () => {
        const { wrapper } = mountLint();
        await nextTick();
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
        expect(nth(links, 0).text().toLowerCase()).toContain("untyped_parameter");
        expect(nth(links, 1).text().toLowerCase()).toContain("step label: input_label");
        expect(nth(links, 2).text().toLowerCase()).toContain("data input: missing an annotation");
        expect(nth(links, 3).text().toLowerCase()).toContain("step label: output");

        // Only 1 non-critical, attribute-related issue
        const attributeLink = wrapper.findAll("[data-description='attribute link']");
        expect(attributeLink.length).toBe(1);
        expect(nth(attributeLink, 0).text().toLowerCase()).toContain("provide readme for your workflow");
    });

    it("emits parameter extraction, input extraction, and unlabeled-output removal actions", async () => {
        const { wrapper } = mountLint();
        const autoFixButton = wrapper.find("[data-description='auto fix lint issues']");
        expect(autoFixButton.exists()).toBe(true);
        await autoFixButton.trigger("click");
        expect(wrapper.emitted("onRefactor")).toHaveLength(1);
        expect(emittedArg(wrapper, "onRefactor")).toMatchObject([
            { action_type: "extract_untyped_parameter", name: "untyped_parameter" },
            { action_type: "extract_input" },
            { action_type: "remove_unlabeled_workflow_outputs" },
        ]);
    });

    it("retains the autofix actions after removing the connected data input", async () => {
        const { wrapper, stepStore } = mountLint();
        stepStore.removeStep(0);
        await nextTick();
        const autoFixButton = wrapper.find("[data-description='auto fix lint issues']");
        expect(autoFixButton.exists()).toBe(true);
        await autoFixButton.trigger("click");
        expect(wrapper.emitted("onRefactor")).toHaveLength(1);
        expect(emittedArg(wrapper, "onRefactor")).toMatchObject([
            { action_type: "extract_untyped_parameter", name: "untyped_parameter" },
            { action_type: "extract_input" },
            { action_type: "remove_unlabeled_workflow_outputs" },
        ]);
    });
});

describe("Lint conditional gates", () => {
    async function mountLint(when: string | undefined, inputConnections: Record<string, unknown>): Promise<VueWrapper> {
        const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
        setActivePinia(pinia);

        const gatedSteps = {
            ...(structuredClone(lintStepsData) as unknown as Steps),
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
            props: {
                lintData: runInTestScope(() => useLintData(ref("1"), gatedStepsRef, ref(testDatatypesMapper))),
                steps: gatedSteps,
                hasChanges: false,
            },
            global: { ...withPlugins(getLocalVue(), pinia), provide: { workflowId: "mock-workflow" } },
        });

        const stepStore = useWorkflowStepStore("mock-workflow");
        Object.values(gatedSteps).map((step) => stepStore.addStep(step));
        await nextTick();
        return wrapper;
    }

    function sectionStatus(wrapper: VueWrapper): string | undefined {
        return wrapper.find("[data-description='linting conditional gates']").attributes("data-lint-status");
    }

    it("says nothing when no step is gated", async () => {
        const wrapper = await mountLint(undefined, {});
        expect(wrapper.find("[data-description='linting conditional gates']").exists()).toBe(false);
    });

    it("passes when a gate reads a connected input", async () => {
        const wrapper = await mountLint("$(inputs.when)", { when: { id: 0, output_name: "output" } });
        expect(sectionStatus(wrapper)).toBe("ok");
    });

    it("warns when a gate reads an input nothing is connected to", async () => {
        const wrapper = await mountLint("$(inputs.when)", {});
        expect(sectionStatus(wrapper)).toBe("warning");
        expect(wrapper.find("[data-description='linting conditional gates']").text()).toContain("gated: when");
    });
});
