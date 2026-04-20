/**
 * Service layer for interaction for the workflow run API.
 */
import axios from "axios";

import { getAppRoot } from "@/onload/loadConfig";
import { errorMessageAsString, rethrowSimple } from "@/utils/simple-error";

/**
 * Error thrown when a workflow cannot run because required tools are not installed.
 * Carries the list of missing tool IDs so callers can offer an installation request.
 */
export class WorkflowMissingToolsError extends Error {
    constructor(message, missingToolIds) {
        super(message);
        this.name = "WorkflowMissingToolsError";
        /** @type {string[]} */
        this.missingToolIds = missingToolIds || [];
    }
}

/**
 * Download the workflow using the 'run' style (see workflow manager on backend
 * for implementation). This contains the data needed to render the UI for workflows.
 *
 * @param {String} workflowId - (Stored?) Workflow ID to fetch data for.
 * @param {String} version - Version of the workflow to fetch.
 */
export async function getRunData(workflowId, version = null, instance = false) {
    let url = `${getAppRoot()}api/workflows/${workflowId}/download?style=run&instance=${instance}`;
    if (version) {
        url += `&version=${version}`;
    }
    try {
        const response = await axios.get(url);
        return response.data;
    } catch (e) {
        const missingToolIds = e?.response?.data?.missing_tool_ids;
        if (missingToolIds && missingToolIds.length > 0) {
            const errMsg = errorMessageAsString(e, "Following tools are not installed.");
            throw new WorkflowMissingToolsError(errMsg, missingToolIds);
        }
        rethrowSimple(e);
    }
}

/**
 * Invoke the specified workflow using the supplied data.
 *
 * @param {String} workflowId - (Stored?) Workflow ID to fetch data for.
 */
export async function invokeWorkflow(workflowId, invocationData) {
    const url = `${getAppRoot()}api/workflows/${workflowId}/invocations`;
    const response = await axios.post(url, invocationData);
    return response.data;
}

/**
 * Request tool step data.
 *
 * @param {String} toolId - Tool ID to fetch data for.
 * @param {String} toolVersion - Corresponding tool version.
 * @param {Object} toolInputs - Current tool state.
 * @param {Object} historyId - History ID to populate data selection fields.
 */
export async function getTool(toolId, toolVersion, toolInputs, historyId) {
    const requestData = {
        tool_id: toolId,
        tool_version: toolVersion,
        inputs: JSON.parse(JSON.stringify(toolInputs)),
        history_id: historyId,
    };
    try {
        const { data } = await axios.post(`${getAppRoot()}api/tools/${toolId}/build`, requestData);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}
