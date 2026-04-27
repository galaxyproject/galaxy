import { GalaxyApi } from "@/api";
import { buildNestedState } from "@/components/Form/utilities";
import { pollUntil } from "@/composables/pollUntil";
import { rethrowSimple } from "@/utils/simple-error";

export async function submitToolJob({ jobDef, formConfig, formData }) {
    const nestedInputs = buildNestedState(formConfig.inputs, formData);
    const request = { ...jobDef, inputs: nestedInputs };
    const { tool_request_id } = await submitJobRequest(request);
    const detail = await waitForToolRequest(tool_request_id);
    return buildJobResponse(detail);
}

async function submitJobRequest(jobRequest) {
    const { data, error } = await GalaxyApi().POST("/api/jobs", {
        body: jobRequest,
    });
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

async function waitForToolRequest(toolRequestId, { pollInterval = 1000, timeout = 600000 } = {}) {
    const terminalState = await pollUntil({
        fn: async () => {
            const { data, error } = await GalaxyApi().GET("/api/tool_requests/{id}/state", {
                params: { path: { id: toolRequestId } },
            });
            if (error) {
                rethrowSimple(error);
            }
            return data;
        },
        condition: (state) => state !== "new",
        interval: pollInterval,
        timeout,
    });

    const { data: detail, error: detailError } = await GalaxyApi().GET("/api/tool_requests/{id}", {
        params: { path: { id: toolRequestId } },
    });
    if (detailError) {
        rethrowSimple(detailError);
    }

    if (terminalState === "failed") {
        const stateMessage = detail.state_message;
        const error = new Error(stateMessage?.err_msg || "Tool request failed");
        error.err_data = stateMessage?.err_data;
        error.err_msg = stateMessage?.err_msg;
        throw error;
    }

    return detail;
}

async function fetchJobOutputs(jobId) {
    const { data, error } = await GalaxyApi().GET("/api/jobs/{job_id}/outputs", {
        params: { path: { job_id: jobId } },
    });
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

async function buildJobResponse(toolRequestDetail) {
    const jobs = toolRequestDetail.jobs.map((j) => ({ id: j.id }));
    const allJobOutputs = await Promise.all(jobs.map((j) => fetchJobOutputs(j.id)));
    const datasetFetches = [];
    const collectionFetches = [];

    for (const jobOutputs of allJobOutputs) {
        for (const out of jobOutputs) {
            if (out.dataset) {
                datasetFetches.push(
                    GalaxyApi()
                        .GET("/api/datasets/{dataset_id}", {
                            params: { path: { dataset_id: out.dataset.id } },
                        })
                        .then(({ data }) => ({ hid: data.hid, name: data.name })),
                );
            }
            if (out.dataset_collection_instance) {
                collectionFetches.push(
                    GalaxyApi()
                        .GET("/api/dataset_collections/{hdca_id}", {
                            params: { path: { hdca_id: out.dataset_collection_instance.id } },
                        })
                        .then(({ data }) => ({ hid: data.hid, name: data.name })),
                );
            }
        }
    }

    const [outputs, output_collections] = await Promise.all([
        Promise.all(datasetFetches),
        Promise.all(collectionFetches),
    ]);

    return {
        jobs,
        outputs,
        output_collections,
    };
}
