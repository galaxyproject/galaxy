import { getFakeDatasetDetails } from "@tests/test-data/datasets";
import { getFakeTool } from "@tests/test-data/tools";
import { HttpResponse } from "msw";

import type { DatasetStorageDetails } from "@/api";
import { http } from "@/api/client/__mocks__/http";
import type { JobDisplayParametersSummary, ShowFullJobResponse } from "@/api/jobs";

export const DETAILS_DATASET = getFakeDatasetDetails({
    id: "cb567c942fb82a10",
    history_id: "a3f8c2e17b90d465",
    name: "Read count summary.tabular",
    extension: "tabular",
    file_ext: "tabular",
    creating_job: "afb72c82cae12034",
    file_size: 128,
    data_type: "galaxy.datatypes.tabular.Tabular",
    peek: "<table><tr><th>sample</th><th>reads</th></tr><tr><td>Sample A</td><td>18420</td></tr></table>",
});

export const DETAILS_JOB: ShowFullJobResponse = {
    id: DETAILS_DATASET.creating_job!,
    model_class: "Job",
    tool_id: "upload1",
    history_id: DETAILS_DATASET.history_id,
    state: "ok",
    create_time: "2024-01-01T00:00:00",
    update_time: "2024-01-01T00:00:01",
    inputs: {},
    outputs: { output0: { id: DETAILS_DATASET.id, src: "hda" } },
    output_collections: {},
    params: { file_type: "tabular" },
    exit_code: 0,
    tool_stdout: "",
    tool_stderr: "",
    job_stdout: "",
    job_stderr: "",
};
export const DETAILS_PARAMETERS: JobDisplayParametersSummary = {
    has_parameter_errors: false,
    parameters: [{ depth: 1, text: "File Format", value: "tabular" }],
    outputs: { output0: [{ label: DETAILS_DATASET.name, value: { id: DETAILS_DATASET.id, src: "hda" } }] },
};
export const DETAILS_STORAGE: DatasetStorageDetails = {
    object_store_id: null,
    name: null,
    description: "Galaxy dataset storage",
    dataset_state: "ok",
    quota: { enabled: false, source: null },
    relocatable: false,
    shareable: true,
    private: false,
    badges: [],
    hashes: [],
    sources: [],
    percent_used: null,
};

/** Dataset storage has no dependency on an associated creating job. */
export function datasetStorageHandler(datasetId = DETAILS_DATASET.id) {
    return http.get("/api/datasets/{dataset_id}/storage", ({ params, response }) =>
        params.dataset_id === datasetId
            ? response(200).json(DETAILS_STORAGE)
            : response("4XX").json({ err_msg: "Dataset not found", err_code: 404001 }, { status: 404 }),
    );
}

/** Complete, terminal upload provenance for the detail page's real child components. */
export function datasetDetailsHandlers() {
    const dataset = DETAILS_DATASET;
    return {
        // This endpoint declares an unknown success payload; HDADetailed validates the detailed view.
        dataset: http.get("/api/datasets/{dataset_id}", ({ params, response }) =>
            params.dataset_id === dataset.id
                ? response.untyped(HttpResponse.json(dataset))
                : response("4XX").json({ err_msg: "Dataset not found", err_code: 404001 }, { status: 404 }),
        ),
        // The legacy tool metadata endpoint is not included in GalaxyApiPaths.
        tool: http.untyped.get("/api/tools/:tool_id", ({ params }) =>
            params.tool_id === DETAILS_JOB.tool_id
                ? HttpResponse.json(
                      getFakeTool({
                          id: DETAILS_JOB.tool_id,
                          name: "Upload File",
                          version: "1.1.7",
                          is_workflow_compatible: false,
                      }),
                  )
                : HttpResponse.json({ err_msg: "Tool not found", err_code: 404001 }, { status: 404 }),
        ),
        job: http.get("/api/jobs/{job_id}", ({ params, response }) =>
            params.job_id === DETAILS_JOB.id
                ? response(200).json(DETAILS_JOB)
                : response("4XX").json({ err_msg: "Job not found", err_code: 404001 }, { status: 404 }),
        ),
        parameters: http.get("/api/datasets/{dataset_id}/parameters_display", ({ params, response }) =>
            params.dataset_id === dataset.id
                ? response(200).json(DETAILS_PARAMETERS)
                : response("4XX").json({ err_msg: "Dataset not found", err_code: 404001 }, { status: 404 }),
        ),
        storage: datasetStorageHandler(),
        inheritance: http.get("/api/datasets/{dataset_id}/inheritance_chain", ({ params, response }) =>
            params.dataset_id === dataset.id
                ? response(200).json([])
                : response("4XX").json({ err_msg: "Dataset not found", err_code: 404001 }, { status: 404 }),
        ),
        metrics: http.get("/api/datasets/{dataset_id}/metrics", ({ params, response }) =>
            params.dataset_id === dataset.id
                ? response(200).json([])
                : response("4XX").json({ err_msg: "Dataset not found", err_code: 404001 }, { status: 404 }),
        ),
        console: http.get("/api/jobs/{job_id}/console_output", ({ params, response }) =>
            params.job_id === DETAILS_JOB.id
                ? response(200).json({ state: "ok", stdout: "", stderr: "" })
                : response("4XX").json({ err_msg: "Job not found", err_code: 404001 }, { status: 404 }),
        ),
        invocations: http.get("/api/invocations", ({ query, response }) =>
            query.get("job_id") === DETAILS_JOB.id
                ? response(200).json([])
                : response("4XX").json({ err_msg: "Job not found", err_code: 404001 }, { status: 404 }),
        ),
    };
}
