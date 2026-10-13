import type { Meta, StoryObj } from "@storybook/vue3-vite";

import {
    INVOCATION,
    invocationGraphHandlers,
    invocationStepHandler,
    invokedWorkflowHandler,
    workflowGraphRateLimited,
} from "@/components/WorkflowInvocationState/test_fixtures";

import WorkflowInvocationSteps from "./WorkflowInvocationSteps.vue";

/** The Steps tab of a scheduled invocation's page, for a workflow that only takes an input. */
const meta = {
    title: "Workflow/Invocation/Graph/WorkflowInvocationSteps",
    component: WorkflowInvocationSteps,
    args: { invocation: INVOCATION, stepsJobsSummary: [] },
    parameters: {
        msw: {
            handlers: { workflow: invokedWorkflowHandler, step: invocationStepHandler, ...invocationGraphHandlers },
        },
    },
} satisfies Meta<typeof WorkflowInvocationSteps>;

export default meta;
type Story = StoryObj<typeof meta>;

/** The workflow's one input, listed on its own rather than grouped. */
export const InputStep: Story = {};

/** A proxy's rate limit refuses the workflow graph's download, so the tab shows why instead of an empty list. */
export const GraphRateLimited: Story = {
    parameters: { msw: { handlers: { workflowGraph: workflowGraphRateLimited } } },
};
