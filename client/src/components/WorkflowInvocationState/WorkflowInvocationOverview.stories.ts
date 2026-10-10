import type { Decorator, Meta, StoryObj } from "@storybook/vue3-vite";
import { HttpResponse } from "msw";
import { h } from "vue";

import { http } from "@/api/client/__mocks__/http";
import { useWorkflowStore } from "@/stores/workflowStore";

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

/** The graph of the invoked workflow. */
export const WorkflowGraph: Story = { decorators: [withWorkflowLoadedBefore] };

/** The invoked workflow belongs to someone else and isn't shared, so there is no graph. */
export const WorkflowNotAccessible: Story = {
    parameters: {
        msw: {
            handlers: {
                workflow: http.get("/api/workflows/{workflow_id}", ({ response }) =>
                    response.untyped(
                        HttpResponse.json(
                            {
                                err_msg: "Workflow is neither importable, nor owned by or shared with current user",
                                err_code: 403002,
                            },
                            { status: 403 },
                        ),
                    ),
                ),
            },
        },
    },
};
