import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { storeToRefs } from "pinia";
import { defineComponent, h, type PropType, ref, toRef } from "vue";

import type { Creator } from "@/api/workflows";
import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import { provideScopedWorkflowStores } from "@/composables/workflowStores";
import type { Steps } from "@/stores/workflowStepStore";

import { useLintData } from "./modules/useLinting";
import lintStepsData from "./test-data/lint_steps.json";

import Lint from "./Lint.vue";

/**
 * A workflow input, a tool step whose dataset input is wired to it and which reads an untyped
 * `${untyped_parameter}`, and an untitled step. The historical fixture leaves steps incomplete, so it
 * is cast.
 */
const INPUT_CONNECTED_STEPS = lintStepsData as unknown as Steps;

/** The same workflow with the tool step's dataset input left unwired. */
const INPUT_DISCONNECTED_STEPS: Steps = {
    ...INPUT_CONNECTED_STEPS,
    1: { ...INPUT_CONNECTED_STEPS[1]!, input_connections: {} },
};

interface LintArgs {
    workflowId: string;
    steps: Steps;
    annotation: string | null;
    readme: string | null;
    license: string | null;
    creator: Creator[] | null;
    hasChanges: boolean;
}

/**
 * Plays the workflow editor's part: loads the steps into the workflow's stores and lints the
 * steps and attributes, then shows the panel. Listeners pass through to the panel.
 */
const LintInEditor = defineComponent({
    name: "LintInEditor",
    compatConfig: { MODE: 3 },
    inheritAttrs: false,
    props: {
        workflowId: { type: String, required: true },
        steps: { type: Object as PropType<Steps>, required: true },
        annotation: { type: String as PropType<string | null>, default: null },
        readme: { type: String as PropType<string | null>, default: null },
        license: { type: String as PropType<string | null>, default: null },
        creator: { type: Array as PropType<Creator[] | null>, default: null },
        hasChanges: { type: Boolean, default: false },
    },
    setup(props, { attrs }) {
        const { stepStore } = provideScopedWorkflowStores(props.workflowId);
        Object.values(props.steps).forEach((step) => stepStore.addStep(step));
        const { steps } = storeToRefs(stepStore);
        const lintData = useLintData(
            toRef(props, "workflowId"),
            steps,
            ref(testDatatypesMapper),
            toRef(props, "annotation"),
            toRef(props, "readme"),
            toRef(props, "license"),
            toRef(props, "creator"),
        );
        return () => h(Lint, { ...attrs, lintData, steps: steps.value, hasChanges: props.hasChanges });
    },
});

// No `component`: the args are the workflow the harness lints, not Lint's props.
const meta = {
    title: "Workflow/Editor/Lint",
    render: (args) => () => h(LintInEditor, args),
    args: {
        workflowId: "f2db41e1fa331b3e",
        steps: INPUT_CONNECTED_STEPS,
        annotation: "Trims reads and maps them to the reference genome.",
        readme: null,
        license: "MIT",
        creator: [{ class: "Person", name: "Jane Doe" }],
        hasChanges: false,
    },
} satisfies Meta<LintArgs>;

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * The step's dataset input is wired to the workflow input, but the step reads an untyped
 * parameter, the workflow input has no annotation, the step's output has no label, and there is
 * no readme.
 */
export const InputConnected: Story = {};

/** The same issues, and the step's dataset input isn't connected to the workflow input. */
export const InputDisconnected: Story = { args: { steps: INPUT_DISCONNECTED_STEPS } };
