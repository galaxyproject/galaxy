import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withCurrentHistory } from "@tests/test-data/currentHistory";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { HttpResponse } from "msw";

import { http } from "@/api/client/__mocks__/http";
import type { StoredWorkflowDetailed } from "@/api/workflows";
import { INVOCATION } from "@/components/WorkflowInvocationState/test_fixtures";

import {
    INVOCATION_HISTORY,
    OWN_WORKFLOW,
    OWN_WORKFLOW_RUNS,
    PUBLISHED_WORKFLOW,
    SIGNED_IN_USER,
} from "./test_fixtures";

import WorkflowAnnotation from "./WorkflowAnnotation.vue";

/** Answers the workflow instance the annotation describes with `storedWorkflow`. */
function workflow(storedWorkflow: StoredWorkflowDetailed) {
    return http.get("/api/workflows/{workflow_id}", ({ response }) =>
        response.untyped(HttpResponse.json(storedWorkflow)),
    );
}

/**
 * The line under a workflow's name on its run form and on an invocation's page: when it was edited
 * or invoked, the history it ran in, and who published it or how often the user has run it.
 */
const meta = {
    title: "Workflow/WorkflowAnnotation",
    component: WorkflowAnnotation,
    decorators: [withCurrentUser(() => SIGNED_IN_USER), withCurrentHistory(INVOCATION_HISTORY)],
    args: { workflowId: INVOCATION.workflow_id, historyId: INVOCATION.history_id },
    parameters: {
        msw: {
            handlers: {
                workflow: workflow(OWN_WORKFLOW),
                runCount: http.get("/api/workflows/{workflow_id}/counts", ({ response }) =>
                    response(200).json(OWN_WORKFLOW_RUNS),
                ),
            },
        },
    },
} satisfies Meta<typeof WorkflowAnnotation>;

export default meta;
type Story = StoryObj<typeof meta>;

/** Running the user's own workflow: when it was edited, its description and how often it has run. */
export const RunForm: Story = { args: { showDetails: true } };

/** An invocation of the user's own workflow, in their current history. */
export const Invocation: Story = { args: { invocationCreateTime: INVOCATION.create_time } };

/** Running a workflow another user published: who published it, and no run count. */
export const PublishedRunForm: Story = {
    args: { showDetails: true },
    parameters: { msw: { handlers: { workflow: workflow(PUBLISHED_WORKFLOW) } } },
};

/** An invocation of a workflow another user published. */
export const PublishedInvocation: Story = {
    args: { invocationCreateTime: INVOCATION.create_time },
    parameters: { msw: { handlers: { workflow: workflow(PUBLISHED_WORKFLOW) } } },
};
