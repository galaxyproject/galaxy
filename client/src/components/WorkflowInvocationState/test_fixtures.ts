import type { Decorator } from "@storybook/vue3-vite";
import { getFakeWorkflowSummary } from "@tests/test-data/workflows";
import { http as mswHttp, HttpResponse } from "msw";
import { h } from "vue";

import { http } from "@/api/client/__mocks__/http";
import type { WorkflowInvocationElementView } from "@/api/invocations";
import type { JobBaseModel, ShowFullJobResponse } from "@/api/jobs";
import type { StoredWorkflowDetailed } from "@/api/workflows";
import { getGalaxyInstance, setGalaxyInstance } from "@/app";
import { GalaxyApp } from "@/app/galaxy";
import { typesAndMappingHandler } from "@/components/Datatypes/test_fixtures";
import { selectableObjectStores } from "@/components/ObjectStore/test_fixtures";
import datasetData from "@/components/providers/test/json/Dataset.json";
import invocationData from "@/components/Workflow/test/json/invocation.json";

import jobStepJobs from "./test/json/jobs.json";

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

/** A mapped concatenate step: one new job, one running job, and two completed jobs. */
export const JOB_STEP_JOBS = jobStepJobs as JobBaseModel[];

/** Each mapped job produces its own output dataset. */
function jobOutputId(jobId: string) {
    return `8c49be448cfe29b${JOB_STEP_JOBS.findIndex(({ id }) => id === jobId)}`;
}

/** Answers the table's runtime lookup and the details opened from any mapped job. */
export const jobStepHandlers = {
    stepJobsSummary: http.get("/api/invocations/{invocation_id}/step_jobs_summary", ({ response }) =>
        response(200).json([
            {
                id: "8c49be448cfe29bc",
                model: "ImplicitCollectionJobs",
                populated_state: "ok",
                states: { new: 1, running: 1, ok: 2 },
            },
        ]),
    ),
    objectStores: selectableObjectStores([]),
    invocationMetrics: http.get("/api/invocations/{invocation_id}/metrics", ({ response }) => response(200).json([])),
    jobDetails: http.get("/api/jobs/{job_id}", ({ params, response }) => {
        const job = JOB_STEP_JOBS.find(({ id }) => id === params.job_id);
        if (!job) {
            throw new Error(`No mapped-job fixture for ${params.job_id}`);
        }
        const details: ShowFullJobResponse = {
            ...job,
            exit_code: job.state === "ok" ? 0 : null,
            inputs: { input1: { id: datasetData.id, src: "hda" } },
            outputs: { out_file1: { id: jobOutputId(job.id), src: "hda" } },
            output_collections: {},
            params: { sleep_time: "0", queries: "[]" },
        };
        return response(200).json(details);
    }),
    jobParameters: http.get("/api/jobs/{job_id}/parameters_display", ({ params, response }) =>
        response(200).json({
            has_parameter_errors: false,
            parameters: [
                { text: "Sleep", depth: 1, value: "0" },
                {
                    text: "Concatenate Dataset",
                    depth: 1,
                    value: [{ id: datasetData.id, src: "hda", name: datasetData.name, hid: datasetData.hid }],
                },
            ],
            outputs: {
                out_file1: [{ label: "Concatenated reads", value: { id: jobOutputId(params.job_id), src: "hda" } }],
            },
        }),
    ),
    jobMetrics: http.get("/api/jobs/{job_id}/metrics", ({ response }) => response(200).json([])),
    consoleOutput: http.get("/api/jobs/{job_id}/console_output", ({ response }) =>
        response(200).json({ stdout: "", stderr: "", state: "running" }),
    ),
    dataset: http.get("/api/datasets/{dataset_id}", ({ params, response }) => {
        const job = JOB_STEP_JOBS.find(({ id }) => jobOutputId(id) === params.dataset_id);
        return response.untyped(
            HttpResponse.json({
                ...datasetData,
                id: params.dataset_id,
                ...(job
                    ? { name: "Concatenated reads", history_id: job.history_id, creating_job: job.id, state: job.state }
                    : {}),
            }),
        );
    }),
    typesAndMapping: typesAndMappingHandler,
};
