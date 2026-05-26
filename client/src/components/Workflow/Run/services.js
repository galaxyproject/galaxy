/**
 * Service layer for interaction for the workflow run API.
 */
import axios from "axios";

import { getAppRoot } from "@/onload/loadConfig";
import { rethrowSimple } from "@/utils/simple-error";

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
        rethrowSimple(e);
    }
}

/**
 * Search history contents (HDAs + HDCAs) for a workflow run dropdown. Filters
 * server-side by extension (canonical accept-set including implicit conversion
 * targets), name/hid (search), and HDA-vs-HDCA type. Returns the raw API list.
 *
 * @param {String} historyId
 * @param {Object} opts
 * @param {Array<string>} [opts.extensions] - sorted accept-set; empty/missing → no extension filter.
 * @param {String} [opts.type] - "dataset" | "dataset_collection".
 * @param {String} [opts.search] - name substring or numeric hid match.
 * @param {Number} [opts.offset]
 * @param {Number} [opts.limit]
 */
export async function searchHistoryContents(historyId, { extensions, type, search, offset = 0, limit = 50 } = {}) {
    const q = [];
    const qv = [];
    q.push("visible-eq");
    qv.push("True");
    q.push("deleted-eq");
    qv.push("False");
    if (type) {
        q.push("history_content_type-eq");
        qv.push(type);
    }
    if (extensions && extensions.length) {
        q.push("extension-in");
        qv.push(extensions.join(","));
    }
    if (search) {
        const trimmed = String(search).trim();
        if (trimmed) {
            if (/^\d+$/.test(trimmed)) {
                q.push("hid-eq");
                qv.push(trimmed);
            } else {
                q.push("name-contains");
                qv.push(trimmed);
            }
        }
    }
    const params = new URLSearchParams();
    params.set("v", "dev");
    params.set("offset", String(offset));
    params.set("limit", String(limit));
    params.set("order", "hid-dsc");
    q.forEach((key) => params.append("q", key));
    qv.forEach((value) => params.append("qv", value));
    try {
        const url = `${getAppRoot()}api/histories/${historyId}/contents?${params.toString()}`;
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
 * @param {String} toolId - Tool ID to fetch data for.
 * @param {String} toolVersion - Corresponding tool version.
 * @param {Object} toolInputs - Current tool state.
 * @param {Object} historyId - History ID to populate data selection fields.
 * @param {Object} optionsPagination - Optional per-parameter pagination spec
 *   (`{<dotted-name>: {<src>: {offset, limit, search}}}`) forwarded as
 *   `options_pagination` so the workflow run form can lazy-load paginated
 *   options or backend-search the dropdown.
 */
export async function getTool(toolId, toolVersion, toolInputs, historyId, optionsPagination) {
    const requestData = {
        tool_id: toolId,
        tool_version: toolVersion,
        inputs: JSON.parse(JSON.stringify(toolInputs)),
        history_id: historyId,
    };
    if (optionsPagination) {
        requestData.options_pagination = optionsPagination;
    }
    try {
        const { data } = await axios.post(`${getAppRoot()}api/tools/${toolId}/build`, requestData);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}
