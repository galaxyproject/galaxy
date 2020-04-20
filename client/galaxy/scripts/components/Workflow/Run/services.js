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
