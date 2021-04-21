/**
 * Simple ajax queries that run against the api.
 *
 * A few history queries still hit routes that don't begin with /api. I have noted them
 * in the comments.
 */

import axios from "axios";
import moment from "moment";
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
    if (response.status != 200) throw new Error(response);
    return response.data;
};

/**
 * Legacy query string rendering. (generates q/qv syntax queries).
 * TODO: remove these converters when the api is modernized.
 *
 * @param {Object} fields Object with parameters to pass to our dumb api
 */

function buildLegacyQueryString(fields = {}) {
    const badParams = buildLegacyParam(fields);
    return Object.keys(badParams)
        .map((key) => `q=${key}&qv=${badParams[key]}`)
        .join("&");
}

function buildLegacyParam(fields = {}) {
    return Object.keys(fields).reduce((result, key) => {
        result[key] = pythonBooleanFormat(fields[key]);
        return result;
    }, {});
}

function pythonBooleanFormat(val) {
    if (val === true) return "True";
    if (val === false) return "False";
    return val;
}

/**
 * Some of the current endpoints don't accept JSON, so we need to
 * do some massaging to send in old form post data.
 * @param {Object} fields
 */

function formData(fields = {}) {
    return Object.keys(fields).reduce((result, fieldName) => {
        result.set(fieldName, fields[fieldName]);
        return result;
    }, new FormData());
}

// #endregion

// #region History Queries

const stdHistoryParams = {
    view: "betawebclient",
};

/**
 * Return list of available histories
 */
export async function getHistoryList() {
    const response = await api.get("/histories", { params: stdHistoryParams });
    return doResponse(response);
}

/**
 * Load one history by id
 * @param {String} id
 */
export async function getHistoryById(id, since) {
    const path = `/histories/${id}`;
    const sinceParam = since !== undefined ? moment.utc(since).toISOString() : null;
    const url = sinceParam ? `${path}?q=update_time-gt&qv=${sinceParam}` : path;
    const response = await api.get(url, { params: stdHistoryParams });
    return doResponse(response);
}

/**
 * Create new history
 * @param {Object} props Optional history props
 */
export async function createNewHistory(props = {}) {
    // TODO: adjust api, keep this for later
    // const url = `/histories`;
    // const data = Object.assign({ name: "New History" }, props);
    // const response = await api.post(url, data, { params: stdHistoryParams });

    // using old route to create and select new history at same time
    const url = prependPath("/history/create_new_current");
    const createResponse = await api.get(url, { baseURL: "" });
    const id = createResponse?.data?.id || null;
    if (!id) {
        throw new Error("failed to create and select new history");
    }
    return doResponse(createResponse);
}

//localhost:8081/history/create_new_current

/**
 * Generates copy of history on server
 * @param {Object} history Source history
 * @param {String} name New history name
 * @param {Boolean} copyAll Copy existing contents
 */
export async function cloneHistory(history, name, copyAll) {
    const url = `/histories`;
    const payload = {
        history_id: history.id,
        name,
        all_datasets: copyAll,
        current: true,
    };
    const response = await api.post(url, payload, { params: stdHistoryParams });
    return doResponse(response);
}

/**
 * Delete history on server
 * @param {String} id Encoded history id
 * @param {Boolean} purge Permanent delete
 */
export async function deleteHistoryById(id, purge = false) {
    const url = `/histories/${id}` + (purge ? "?purge=True" : "");
    const response = await api.delete(url, { params: stdHistoryParams });
    return doResponse(response);
}

/**
 * Undelete a deleted (but not purged) history
 * @param {String} id Encoded history id
 */
export async function undeleteHistoryById(id) {
    const url = `/histories/deleted/${id}/undelete`;
    const response = await api.post(url, null, { params: stdHistoryParams });
    return doResponse(response);
}

/**
 * Update specific fields in history
 * @param {Object} history
 * @param {Object} payload fields to update
 */
export async function updateHistoryFields(id, payload) {
    const url = `/histories/${id}`;
    const response = await api.put(url, payload, { params: stdHistoryParams });
    return doResponse(response);
}

/**
 * Set permissions to private for indicated history
 * TODO: rewrite API endpoint for this
 * @param {String} history_id
 */
export async function secureHistory(history) {
    // NOTE: does not hit normal api/ endpoint
    const { id } = history;
    const url = prependPath("/history/make_private");
    const response = await axios.post(url, formData({ history_id: id }));
    if (response.status != 200) {
        throw new Error(response);
    }
    // instead of a full lookup we could alternately figure out if
    // just a couple fields are changed and return the model with those
    // fields updated. it would avoid an extraneous ajax call
    return await getHistoryById(id);
}

// #endregion

// #region "Current History"

export async function getCurrentHistoryFromServer() {
    const url = "/history/current_history_json";
    const response = await api.get(url, {
        baseURL: prependPath("/"), // old api doesn't use api path
    });
    return doResponse(response);
}

export async function setCurrentHistoryOnServer(history_id) {
    const url = "/history/set_as_current";
    // TODO: why is this a GET?
    // Doesn't matter, it shouldn't exist at all
    const response = await api.get(url, {
        baseURL: prependPath("/"), // old api doesn't use api path
        params: { id: history_id },
    });
    return doResponse(response);
}

// #endregion

// #region Content Queries

/**
 * Loads specific fields for provided content object, handy for loading
 * visualizations or any other field that's too unwieldy to reasonably include
 * in the standard content caching cycle.
 *
 * @param {Object} content content object
 * @param {Array} fields Array of fields to load
 */
export async function loadContentFields(content, fields = []) {
    if (fields.length) {
        const { history_id, id, history_content_type: type } = content;
        const url = `/histories/${history_id}/contents/${type}s/${id}`;
        const params = { keys: fields.join(",") };
        const response = await api.get(url, { params });
        if (response.status != 200) {
            throw new Error(response);
        }
        return response.data;
    }
    return null;
}

/**
 * Generic content query function originally intended to help with bulk updates
 * so we don't have to go through the legacy /history endpoints and
 * can stay in the /api as much as possible.
 *
 * @param {*} history
 * @param {*} filterParams
 */
export async function getAllContentByFilter(history, filterParams = {}) {
    const { id } = history;
    const strFilter = buildLegacyQueryString(filterParams);
    const params = { v: "dev", view: "summary", keys: "file_size,accessible,creating_job,job_source_id" };
    const url = `/histories/${id}/contents?${strFilter}`;
    const response = await api.get(url, { params });
    return doResponse(response);
}

/**
 * Given a content object, retrieve the detailed dataset or collection
 * object by looking at the url prop of the content
 * @param {Object} content Content object
 * @param {Object} params key/value search parameters
 */
export async function getContentDetails(content, params = {}) {
    const { history_id, id, history_content_type } = content;
    const url = `/histories/${history_id}/contents/${history_content_type}s/${id}`;
    const response = await api.get(url, { params });
    return doResponse(response);
}

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
 * Undeletes content flagged as deleted.
 * @param {Object} content
 */
export async function undeleteContent(content) {
    return await updateContentFields(content, {
        deleted: false,
    });
}

/**
 * Marks as purged
 * @param {*} history
 * @param {*} content
 */
export async function purgeContent(history, content) {
    const url = `/histories/${history.id}/contents/${content.id}?purge=True`;
    const response = await api.delete(url);
    return doResponse(response);
}

/**
 * Bulk update endpoint (TODO: rewrite)
 *
 * @param {*} history
 * @param {*} type_ids
 * @param {*} fields
 */
export async function bulkContentUpdate(history, type_ids = [], fields = {}) {
    const items = type_ids.map((type_id) => {
        const [history_content_type, id] = type_id.split("-");
        return { id, type_id, history_content_type };
    });

    const { id } = history;
    const url = `/histories/${id}/contents?view=betawebclient`;
    const payload = Object.assign({}, fields, { items });
    const response = await api.put(url, payload);
    console.log("bulkContentUpdate response", response);
    return doResponse(response);
}

// #endregion

// #region Collections

export async function createDatasetCollection(history, inputs = {}) {
    const defaults = {
        collection_type: "list",
        copy_elements: true,
        name: "list",
        element_identifiers: [],
        hide_source_items: "True",
        type: "dataset_collection",
    };

    const payload = Object.assign({}, defaults, inputs);
    const url = `/histories/${history.id}/contents?view=betawebclient`; // keys=${keys}`;
    const response = await api.post(url, payload);
    return doResponse(response);
}

export async function deleteDatasetCollection(collection, recursive = false, purge = false) {
    const { history_id, id } = collection;
    const url = `/histories/${history_id}/contents/dataset_collections/${id}`;
    const params = buildLegacyParam({ recursive, purge });
    const response = await api.delete(url, { params });
    return doResponse(response);
}

// #endregion

// #region Job Queries

const jobStash = new Map();
const toolStash = new Map();

export async function loadJobById(jobId) {
    if (!jobStash.has(jobId)) {
        const url = `/jobs/${jobId}?full=false`;
        const response = await api.get(url);
        const job = response.data;
        jobStash.set(jobId, job);
    }
    return jobStash.get(jobId);
}

export async function loadToolForJob(job) {
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

// #endregion
