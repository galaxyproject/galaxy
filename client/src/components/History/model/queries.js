/**
 * Simple ajax queries that run against the api.
 *
 * A few history queries still hit routes that don't begin with /api. I have noted them
 * in the comments.
 */

import axios from "axios";
import { prependPath } from "utils/redirect";

// #region setup & utils

/**
 * Prefix axios with configured path prefix and /api
 */

const api = axios.create({
    baseURL: prependPath("/api"),
});

/**
 * Generic json getter
 * @param {*} response
 */

const doResponse = (response) => {
    if (response.status != 200) {
        throw new Error(response);
    }
    return response.data;
};

/**
 * Legacy query string rendering. (generates q/qv syntax queries).
 * TODO: remove these converters when the api is modernized.
 */
function buildQueryStringFrom(filters) {
    const queryString = Object.entries(filters)
        .map(([f, v]) => `q=${f}&qv=${v}`)
        .join("&");
    return queryString;
}

// #endregion

/**
 * Content Queries
 */

/**
 * Deletes item from history
 *
 * @param {Object} content Content object
 * @param {Boolean} purge Permanent delete
 * @param {Boolean} recursive Scorch the earth?
 */
export async function deleteContent(content, deleteParams = {}) {
    const defaults = { purge: false, recursive: false };
    const params = Object.assign({}, defaults, deleteParams);
    const { history_id, history_content_type, id } = content;
    const url = `/histories/${history_id}/contents/${history_content_type}s/${id}`;
    const response = await api.delete(url, { params });
    return doResponse(response);
}

/**
 * Update specific fields on datasets or collections.
 * @param {Object} content content object
 * @param {Object} newFields key/value object of properties to update
 */
export async function updateContentFields(content, newFields = {}) {
    const { history_id, id, history_content_type: type } = content;
    const url = `/histories/${history_id}/contents/${type}s/${id}`;
    const response = await api.put(url, newFields);
    return doResponse(response);
}

/**
 * Performs an operation on a specific set of items or all the items
 * matching the filters.
 * If a specific set of items is provided, the filters are ignored, otherwise
 * the filters will determine which items are processed.
 *
 * @param {Object} history The history that contains the items
 * @param {String} operation The operation to perform on all items
 * @param {Object} filters The filter query parameters
 * @param {Object[]} items The set of items to process as `{ id, history_content_type }`
 */
export async function bulkUpdate(history, operation, filters, items = []) {
    const { id } = history;
    const filterQuery = buildQueryStringFrom(filters);
    const url = `/histories/${id}/contents/bulk?${filterQuery}`;
    const payload = {
        operation,
        items,
    };
    const response = await api.put(url, payload);
    console.debug(`Submitted request to ${operation} selected content in bulk.`, response);
    return doResponse(response);
}

/**
 * Collections
 */

export async function createDatasetCollection(history, inputs = {}) {
    const defaults = {
        collection_type: "list",
        copy_elements: true,
        name: "list",
        element_identifiers: [],
        hide_source_items: true,
        type: "dataset_collection",
    };

    const payload = Object.assign({}, defaults, inputs);
    const url = `/histories/${history.id}/contents`;
    const response = await api.post(url, payload);
    return doResponse(response);
}

/**
 * Job Queries
 */
const jobStash = new Map();
const toolStash = new Map();

async function loadJobById(jobId) {
    if (!jobStash.has(jobId)) {
        const url = `/jobs/${jobId}?full=false`;
        const response = await api.get(url);
        const job = response.data;
        jobStash.set(jobId, job);
    }
    return jobStash.get(jobId);
}

async function loadToolForJob(job) {
    const { tool_id, history_id } = job;
    const key = `${tool_id}-${history_id}`;
    if (!toolStash.has(key)) {
        const url = `/tools/${tool_id}/build?history_id=${history_id}`;
        const response = await api.get(url);
        const tool = response.data;
        toolStash.set(key, tool);
    }
    return toolStash.get(key);
}

export async function loadToolFromJob(jobId) {
    const job = await loadJobById(jobId);
    return await loadToolForJob(job);
}
