import type { Decorator } from "@storybook/vue3-vite";
import { getFakeWorkflowSummary } from "@tests/test-data/workflows";
import { http as mswHttp, HttpResponse } from "msw";
import { h } from "vue";
import { http } from "@/api/client/__mocks__/http";
import type { WorkflowInvocationElementView } from "@/api/invocations";
import type { StoredWorkflowDetailed } from "@/api/workflows";
import { getGalaxyInstance, setGalaxyInstance } from "@/app";
import { GalaxyApp } from "@/app/galaxy";
import { typesAndMappingHandler } from "@/components/Datatypes/test_fixtures";
import datasetData from "@/components/providers/test/json/Dataset.json";
import invocationData from "@/components/Workflow/test/json/invocation.json";

/** A scheduled invocation of a workflow that takes one input dataset. */
export const INVOCATION = invocationData as unknown as WorkflowInvocationElementView;

const INPUT_STEP = invocationData.steps[0]!;

const INPUT_DATASET = invocationData.inputs["0"];

/** The stored workflow the invocation ran, as `/api/workflows/{id}?instance=true` returns it. */
export const INVOKED_WORKFLOW: StoredWorkflowDetailed = {
    ...getFakeWorkflowSummary(),
    model_class: "StoredWorkflow",
    annotation: null,
    email_hash: null,
    help: null,
    readme: null,
    slug: null,
    version: 0,
    inputs: { 0: { label: INPUT_STEP.workflow_step_label, uuid: INPUT_STEP.workflow_step_uuid, value: "" } },
    steps: { 0: { id: 0, type: "data_input", annotation: null, input_steps: {}, when: null } },
};

/** The invoked workflow as the graph loads it: one dataset input. */
const EDITOR_WORKFLOW = {
    id: INVOKED_WORKFLOW.id,
    name: INVOKED_WORKFLOW.name,
    version: 0,
    annotation: "",
    tags: [],
    comments: [],
    steps: {
        0: {
            id: 0,
            type: "data_input",
            label: INPUT_STEP.workflow_step_label,
            name: "Input dataset",
            content_id: null,
            tool_state: {},
            errors: null,
            inputs: [],
            outputs: [{ name: "output", extensions: ["input"], optional: false }],
            annotation: "",
            post_job_actions: {},
            uuid: INPUT_STEP.workflow_step_uuid,
            workflow_outputs: [],
            input_connections: {},
            position: { left: 0, top: 0 },
        },
    },
};

/** Answers what the invocation graph loads: the invoked workflow's steps, its input dataset and datatypes. */
export const invocationGraphHandlers = {
    // Not in the API schema: the graph loads the editor view with axios.
    workflowGraph: http.untyped.get("/api/workflows/:workflow_id/download", () => HttpResponse.json(EDITOR_WORKFLOW)),
    inputDataset: http.get("/api/datasets/{dataset_id}", ({ response }) =>
        response.untyped(
            HttpResponse.json({ ...datasetData, id: INPUT_DATASET.id, history_id: invocationData.history_id }),
        ),
    ),
    typesAndMapping: typesAndMappingHandler,
};

/** Answers the details each listed step loads: the input step, scheduled with no jobs, so nothing polls. */
export const invocationStepHandler = http.get("/api/invocations/steps/{step_id}", ({ params, response }) =>
    response.untyped(HttpResponse.json({ ...INPUT_STEP, id: params.step_id })),
);

/** Answers the workflow fetch with the invoked workflow, for views that fetch it themselves. */
export const invokedWorkflowHandler = http.get("/api/workflows/{workflow_id}", ({ response }) =>
    response.untyped(HttpResponse.json(INVOKED_WORKFLOW)),
);

/**
 * nginx's rate limit refuses the graph's workflow download, as Galaxy's Sentry saw it. Plain `msw`, since
 * the typed handlers stamp failures with Galaxy's request id, and a proxy's page carries none.
 */
export const workflowGraphRateLimited = mswHttp.get(
    "/api/workflows/:workflow_id/download",
    () =>
        new HttpResponse(
            "<html><head><title>429 Too Many Requests</title></head><body><center><h1>429 Too Many Requests</h1></center><hr><center>nginx</center></body></html>",
            { status: 429, headers: { "Content-Type": "text/html" } },
        ),
);

/** The workflow graph draws its nodes with the app's legacy Galaxy instance. */
export const withGalaxyInstance: Decorator = (story) => ({
    setup() {
        if (!getGalaxyInstance()) {
            setGalaxyInstance(new GalaxyApp({ config: { enable_tool_recommendations: false } }));
        }
    },
    render: () => h(story()),
});
