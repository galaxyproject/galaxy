import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { storeToRefs } from "pinia";
import { expect } from "storybook/test";
import { defineComponent, h, type PropType, ref, toRef } from "vue";

import type { Creator } from "@/api/workflows";
import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import { provideScopedWorkflowStores } from "@/composables/workflowStores";
import type { Steps } from "@/stores/workflowStepStore";

import {
    bestPracticeWarningAnnotation,
    bestPracticeWarningCreator,
    bestPracticeWarningLicense,
    bestPracticeWarningReadme,
} from "./modules/linting";
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

type PlayContext = Parameters<NonNullable<Story["play"]>>[0];
type Canvas = PlayContext["canvas"];

/** Each check the review lists, in order: what it says when it passes, and when it fails. */
const CHECKS = {
    formalInputs: [
        "Workflow parameters are using formal input parameters.",
        "This workflow uses legacy workflow parameters. They should be replaced with formal workflow inputs. Formal input parameters make tracking workflow provenance, usage within subworkflows, and executing the workflow via the API more robust:",
    ],
    connectedInputs: [
        "All non-optional inputs to workflow steps are connected to formal input parameters.",
        "Some non-optional inputs are not connected to formal workflow inputs. Formal input parameters make tracking workflow provenance, usage within subworkflows, and executing the workflow via the API more robust:",
    ],
    inputMetadata: [
        "All workflow inputs have labels and annotations.",
        "Some workflow inputs are missing labels and/or annotations:",
    ],
    uniqueOutputLabels: [
        "All workflow output labels are unique.",
        "Some workflow outputs have duplicate labels. Workflow output labels must be unique:",
    ],
    labeledOutputs: [
        "All workflow outputs have valid (populated) labels.",
        "The following workflow outputs have no labels, they should be assigned a useful label or unchecked in the workflow editor to mark them as no longer being a workflow output:",
    ],
    annotation: ["This workflow has a short description.", bestPracticeWarningAnnotation],
    readme: ["This workflow has a readme.", bestPracticeWarningReadme],
    creator: ["This workflow defines creator information.", bestPracticeWarningCreator],
    license: ["This workflow defines a license.", bestPracticeWarningLicense],
} as const;

/** Checks each check reads as passing, unless it's one of `failing`, and never both ways. */
async function seeChecks(canvas: Canvas, failing: (keyof typeof CHECKS)[]) {
    for (const [check, [passes, fails]] of Object.entries(CHECKS)) {
        const failed = failing.includes(check as keyof typeof CHECKS);
        await expect(canvas.getByText(failed ? fails : passes)).toBeVisible();
        await expect(canvas.queryByText(failed ? passes : fails)).not.toBeInTheDocument();
    }
}

/** Checks a group's heading and its tally of resolved issues, also given as its icon's title. */
async function seeTally(canvas: Canvas, group: "critical" | "attributes", resolved: number, total: number) {
    const heading = `${group.charAt(0).toUpperCase()}${group.slice(1)} Best Practices`;
    const tally = `${resolved} out of ${total} ${group} best practice issues resolved`;
    await expect(canvas.getByText(heading).parentElement).toHaveTextContent(
        new RegExp(`^${heading} ${tally} ${resolved} / ${total}$`),
    );
    await expect(canvas.getByRole("img", { name: tally })).toBeVisible();
}

/**
 * Checks the review's buttons, in order: fix all, then a fix or a look per issue. The untyped
 * parameter's reads "Step 2 : untyped_parameter": it names the tool input, which has no `label` in
 * `lint_steps.json`.
 */
async function seeFixes(canvas: Canvas, fixes: string[]) {
    await expect(
        canvas.getAllByRole("button").map((button) => button.textContent?.replace(/\s+/g, " ").trim()),
    ).toEqual(fixes);
}

/**
 * The step's dataset input is wired to the workflow input, but the step reads an untyped
 * parameter, the workflow input has no annotation, the step's output has no label, and there is
 * no readme.
 */
export const InputConnected: Story = {
    play: async ({ canvas, step }) => {
        await step("Read three critical issues and the missing readme", async () => {
            await seeTally(canvas, "critical", 2, 5);
            await seeTally(canvas, "attributes", 3, 4);
            await seeChecks(canvas, ["formalInputs", "inputMetadata", "labeledOutputs", "readme"]);
        });
        await step("See a fix for each issue, with no fix for a connected input", async () => {
            await seeFixes(canvas, [
                "Try to automatically fix issues.",
                "Step 2 : untyped_parameter",
                "Step 1 data input: Missing an annotation",
                "Step 2 step label: output",
                "Provide Readme for your Workflow.",
            ]);
        });
    },
};

/** The same issues, and the step's dataset input isn't connected to the workflow input. */
export const InputDisconnected: Story = {
    args: { steps: INPUT_DISCONNECTED_STEPS },
    play: async ({ canvas, step }) => {
        await step("Read four passing checks and five issues", async () => {
            await seeTally(canvas, "critical", 1, 5);
            await seeTally(canvas, "attributes", 3, 4);
            await seeChecks(canvas, ["formalInputs", "connectedInputs", "inputMetadata", "labeledOutputs", "readme"]);
        });
        await step("See a fix for each issue, in the order listed", async () => {
            await seeFixes(canvas, [
                "Try to automatically fix issues.",
                "Step 2 : untyped_parameter",
                "Step 2 step label: input_label",
                "Step 1 data input: Missing an annotation",
                "Step 2 step label: output",
                "Provide Readme for your Workflow.",
            ]);
        });
    },
};
