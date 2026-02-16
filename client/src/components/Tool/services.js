import axios from "axios";

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
    const url = `${getAppRoot()}api/jobs`;
    const { data } = await axios.post(url, jobRequest);
    return data;
}

/** Poll GET /api/tool_requests/{id}/state until terminal state.
 * Returns the ToolRequestDetailedModel on success.
 * Throws on failure with the state_message from the server.
 */
export async function waitForToolRequest(toolRequestId, { pollInterval = 1000, maxAttempts = 600 } = {}) {
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
        const stateUrl = `${getAppRoot()}api/tool_requests/${toolRequestId}/state`;
        const { data: state } = await axios.get(stateUrl);
        if (state === "submitted") {
            const detailUrl = `${getAppRoot()}api/tool_requests/${toolRequestId}`;
            const { data: detail } = await axios.get(detailUrl);
            return detail;
        }
        if (state === "failed") {
            const detailUrl = `${getAppRoot()}api/tool_requests/${toolRequestId}`;
            const { data: detail } = await axios.get(detailUrl);
            throw new Error(detail.state_message || "Tool request failed");
        }
        await new Promise((resolve) => setTimeout(resolve, pollInterval));
    }
    throw new Error("Tool request timed out waiting for completion");
}

/** Fetch output datasets and collections for a completed job.
 * Returns an array of JobOutputAssociation | JobOutputCollectionAssociation.
 */
export async function fetchJobOutputs(jobId) {
    const url = `${getAppRoot()}api/jobs/${jobId}/outputs`;
    const { data } = await axios.get(url);
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
                    axios
                        .get(`${getAppRoot()}api/datasets/${out.dataset.id}`)
                        .then((r) => ({ hid: r.data.hid, name: r.data.name })),
                );
            }
            if (out.dataset_collection_instance) {
                collectionFetches.push(
                    axios
                        .get(`${getAppRoot()}api/dataset_collections/${out.dataset_collection_instance.id}`)
                        .then((r) => ({ hid: r.data.hid, name: r.data.name })),
                );
            }
        }
    }

    const [outputs, output_collections] = await Promise.all([
        Promise.all(datasetFetches),
        Promise.all(collectionFetches),
    ]);

    return {
        produces_entry_points: false,
        jobs,
        outputs,
        output_collections,
    };
}
