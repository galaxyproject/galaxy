import axios from "axios";

import { GalaxyApi } from "@/api";
import { pollUntil } from "@/composables/pollUntil";
import { getAppRoot } from "@/onload/loadConfig";
import { rethrowSimple } from "@/utils/simple-error";

export async function updateToolFormData(tool_id, tool_uuid, tool_version, history_id, inputs) {
    const current_state = {
        tool_id: tool_id,
        tool_uuid: tool_uuid,
        tool_version: tool_version,
        inputs: inputs,
        history_id: history_id,
    };
    const url = `${getAppRoot()}api/tools/${tool_uuid || tool_id}/build`;
    try {
        const { data } = await axios.post(url, current_state);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

/** Tools data request helper **/
export async function getToolFormData(tool_id, tool_version, job_id, history_id) {
    let url = "";
    const data = {};

    // build request url and collect request data
    if (job_id) {
        url = `${getAppRoot()}api/jobs/${job_id}/build_for_rerun`;
    } else {
        url = `${getAppRoot()}api/tools/${tool_id}/build`;
        const queryString = window.location.search;
        const params = new URLSearchParams(queryString);
        for (const [key, value] of params.entries()) {
            if (key != "tool_id") {
                data[key] = value;
            }
        }
    }
    history_id && (data["history_id"] = history_id);
    tool_version && (data["tool_version"] = tool_version);

    // attach data to request url
    if (Object.entries(data).length != 0) {
        const params = new URLSearchParams(data);
        url = `${url}?${params.toString()}`;
    }

    // request tool data
    try {
        const { data } = await axios.get(url);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

/** Submit a job via the async POST /api/jobs endpoint.
 * Returns { tool_request_id, task_result }.
 */
export async function submitJobRequest(jobRequest) {
    const { data, error } = await GalaxyApi().POST("/api/jobs", {
        body: jobRequest,
    });
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

/** Poll GET /api/tool_requests/{id}/state until terminal state.
 * Returns the ToolRequestDetailedModel on success.
 * Throws on failure with the state_message from the server.
 */
export async function waitForToolRequest(toolRequestId, { pollInterval = 1000, timeout = 600000 } = {}) {
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

/** Fetch output datasets and collections for a completed job.
 * Returns an array of JobOutputAssociation | JobOutputCollectionAssociation.
 */
export async function fetchJobOutputs(jobId) {
    const { data, error } = await GalaxyApi().GET("/api/jobs/{job_id}/outputs", {
        params: { path: { job_id: jobId } },
    });
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

/** Build a JobResponse-compatible object from a completed ToolRequestDetailedModel.
 * Fetches job outputs and resolves dataset details for the success page.
 * @param {Object} toolRequestDetail - The ToolRequestDetailedModel from polling
 * @returns {Object} Compatible with JobResponse { produces_entry_points, jobs, outputs, output_collections }
 */
export async function buildJobResponse(toolRequestDetail) {
    const jobs = toolRequestDetail.jobs.map((j) => ({ id: j.id }));

    // Fetch outputs for all jobs in parallel
    const allJobOutputs = await Promise.all(jobs.map((j) => fetchJobOutputs(j.id)));

    // Collect dataset and collection IDs from job outputs
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
