import type { Decorator, Meta, StoryObj } from "@storybook/vue3-vite";
import { HttpResponse } from "msw";
import { expect } from "storybook/test";
import { h } from "vue";

import { http } from "@/api/client/__mocks__/http";
import { useWorkflowStore } from "@/stores/workflowStore";
import { escapeRegExp } from "@/utils/regExp";

import { INVOCATION, invocationGraphHandlers, INVOKED_WORKFLOW, withGalaxyInstance } from "./test_fixtures";

import WorkflowInvocationOverview from "./WorkflowInvocationOverview.vue";

/** The invoked workflow was loaded before, so the overview doesn't fetch it. */
const withWorkflowLoadedBefore: Decorator = (story) => ({
    setup() {
        useWorkflowStore().workflowsByInstanceId[INVOCATION.workflow_id] = INVOKED_WORKFLOW;
    },
    render: () => h(story()),
});

/** The Overview tab of a finished invocation's page, for a workflow that only takes an input. */
const meta = {
    title: "WorkflowInvocationState/WorkflowInvocationOverview",
    component: WorkflowInvocationOverview,
    decorators: [withGalaxyInstance],
    args: { invocation: INVOCATION, invocationAndJobTerminal: true, stepsJobsSummary: [] },
    parameters: { msw: { handlers: invocationGraphHandlers } },
} satisfies Meta<typeof WorkflowInvocationOverview>;

export default meta;
type Story = StoryObj<typeof meta>;

const UNOWNED_MESSAGE = "Workflow is neither importable, nor owned by or shared with current user";

/** The graph of the invoked workflow. */
export const WorkflowGraph: Story = {
    decorators: [withWorkflowLoadedBefore],
    play: async ({ canvas, step }) => {
        await step("See the workflow's input step and the dataset it ran on", async () => {
            await expect(await canvas.findByText("input dataset", {}, { timeout: 5000 })).toBeVisible();
            const dataset = canvas.getByText("M117C1-ch_2.fq.fastqsanger");
            await expect(dataset.tagName).toBe("B");
            await expect(dataset.parentElement).toHaveTextContent(/^8: M117C1-ch_2\.fq\.fastqsanger$/);
        });
        await step("See no alert, only the graph's hint to click a step", async () => {
            await expect(canvas.queryByRole("alert")).not.toBeInTheDocument();
            await expect(canvas.getAllByRole("status").map((status) => status.textContent?.trim())).toEqual([
                "Click on a step in the workflow graph above to view its details.",
            ]);
        });
    },

    // TODO a11y: label-content-name-mismatch (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** The invoked workflow belongs to someone else and isn't shared, so there is no graph. */
export const WorkflowNotAccessible: Story = {
    parameters: {
        msw: {
            handlers: {
                workflow: http.get("/api/workflows/{workflow_id}", ({ response }) =>
                    response.untyped(
                        HttpResponse.json(
                            {
                                err_msg: UNOWNED_MESSAGE,
                                err_code: 403002,
                            },
                            { status: 403 },
                        ),
                    ),
                ),
            },
        },
    },
    play: async ({ canvas, step }) => {
        await step("See why the workflow can't be shown", async () => {
            await expect(await canvas.findByRole("alert", {}, { timeout: 5000 })).toHaveTextContent(
                new RegExp(`^Failed to retrieve workflow\\. ${escapeRegExp(UNOWNED_MESSAGE)}$`),
            );
        });
        await step("See no graph and nothing still loading", async () => {
            await expect(canvas.queryByText("input dataset")).not.toBeInTheDocument();
            await expect(canvas.queryByRole("button", { name: "Zoom In" })).not.toBeInTheDocument();
            await expect(canvas.queryByRole("status")).not.toBeInTheDocument();
        });
    },
};
