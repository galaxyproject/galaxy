import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect, userEvent, within } from "storybook/test";

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

const INPUT_STEP_TITLE = "Step 1: input dataset";

/** The workflow's one input, listed on its own rather than grouped. */
export const InputStep: Story = {
    play: async ({ canvasElement, step }) => {
        const canvas = within(canvasElement);
        await step("List the input step under the search box, outside a Workflow Inputs group", async () => {
            expect(await canvas.findByText(INPUT_STEP_TITLE, {}, { timeout: 5000 })).toBeVisible();
            expect(canvas.getByPlaceholderText("search steps")).toBeVisible();
            expect(canvas.queryByText("Workflow Inputs")).toBeNull();
        });
    },
};

/** Searches the steps for a title none of them has. */
export const SearchMatchesNoStep: Story = {
    play: async ({ canvasElement, step }) => {
        const canvas = within(canvasElement);
        await step("Wait for the steps to list", async () => {
            await canvas.findByText(INPUT_STEP_TITLE, {}, { timeout: 5000 });
        });
        await step("Search for a step the workflow doesn't have", async () => {
            await userEvent.type(canvas.getByPlaceholderText("search steps"), "trimmer");
            expect(await canvas.findByText("No steps match the search query.")).toBeVisible();
            expect(canvas.queryByText(INPUT_STEP_TITLE)).toBeNull();
        });
    },
};

/** A proxy's rate limit refuses the workflow graph's download, so the tab shows why instead of an empty list. */
export const GraphRateLimited: Story = {
    parameters: { msw: { handlers: { workflowGraph: workflowGraphRateLimited } } },
    play: async ({ canvasElement, step }) => {
        const canvas = within(canvasElement);
        await step("Explain the refused download in place of the steps", async () => {
            const alert = await canvas.findByRole("alert", {}, { timeout: 5000 });
            // nginx's page carries no Galaxy message, so the client describes the status instead.
            expect(alert).toHaveTextContent(/^Too many requests, please wait and try again \(429\)$/);
            expect(canvas.queryByText(/^Loading invocation steps/)).toBeNull();
            expect(canvas.queryByPlaceholderText("search steps")).toBeNull();
            expect(canvas.queryByText("There are no steps to display.")).toBeNull();
        });
    },
};
