/**
 * Service layer for interaction for the workflow run API.
 */
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
import { rethrowSimple } from "utils/simple-error";

/**
 * Download the workflow using the 'run' style (see workflow manager on backend
 * for implementation). This contains the data needed to render the UI for workflows.
 *
 * @param {String} workflowId - (Stored?) Workflow ID to fetch data for.
 */
export async function getRunData(workflowId) {
    const url = `${getAppRoot()}api/workflows/${workflowId}/download?style=run`;
    try {
        const response = await axios.get(url);
        return response.data;
    } catch (e) {
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
 * @param {String} workflowId - (Stored?) Workflow ID to fetch data for.
 */
export async function getTool(toolId, toolVersion, toolInputs) {
    const requestData = {
        tool_id: toolId,
        tool_version: toolVersion,
        inputs: $.extend(true, {}, toolInputs),
    };
    try {
        const { data } = await axios.post(`${getAppRoot()}api/tools/${toolId}/build`, requestData);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}
