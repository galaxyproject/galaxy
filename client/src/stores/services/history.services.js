import axios from "axios";
import { prependPath } from "utils/redirect";

/**
 * Generic json getter
 * @param {*} response
 * @return {Object} response.data or throws an error if response status is not 200
 */
function doResponse(response) {
    if (response.status !== 200) {
        throw new Error(response);
    }
    return response.data;
}

/**
 * Some current endpoints don't accept JSON, so we need to
 * do some massaging to send in old form post data.
 * @param {Object} fields
 */
function formData(fields = {}) {
    return Object.keys(fields).reduce((result, fieldName) => {
        result.set(fieldName, fields[fieldName]);
        return result;
    }, new FormData());
}

/**
 * Default history request parameters.
 */
const stdHistoryParams = {
    view: "summary",
};

/**
 * Extended history request parameters.
 * Retrieves additional details which are usually more "expensive".
 */
const extendedHistoryParams = {
    view: "summary",
    keys: "size,contents_active,user_id",
};

/**
 * Create a new history, select it as the current history, and return it if successful.
 * @return {Object} the new history or throws an error if new history creation fails
 */
export async function createAndSelectNewHistory() {
    const url = "history/create_new_current";
    const response = await axios.get(prependPath(url));
    const newHistoryId = response?.data?.id || null;
    if (!newHistoryId) {
        throw new Error("failed to create and select new history");
    }
    return doResponse(response);
}

/**
 * Generates copy of history on server.
 * @param {Object} history Source history
 * @param {String} name New history name
 * @param {Boolean} copyAll Copy existing contents
 */
export async function cloneHistory(history, name, copyAll) {
    const url = "api/histories";
    const payload = {
        name,
        current: true,
        all_datasets: copyAll,
        history_id: history.id,
    };
    const response = await axios.post(prependPath(url), payload, { params: stdHistoryParams });
    return doResponse(response);
}

/**
 * Delete history on server and return the deleted history.
 * @param {String} id Encoded history id
 * @param {Boolean} [purge=false] Permanent delete
 */
export async function deleteHistoryById(id, purge = false) {
    const url = `api/histories/${id}` + (purge ? "?purge=True" : "");
    const response = await axios.delete(prependPath(url), { params: stdHistoryParams });
    return doResponse(response);
}

/**
 * Get current history from server and return it.
 * @param {String} since timestamp to get histories since
 * @return {Object} the current history
 */
export async function getCurrentHistoryFromServer(since = undefined) {
    const url = "history/current_history_json";
    const response = await axios.get(prependPath(url), { params: { since: since } });
    return doResponse(response);
}

/**
 * Set current history on server and return it.
 * @param {String} historyId Encoded history id
 * @return {Object} the current history
 */
export async function setCurrentHistoryOnServer(historyId) {
    const url = "history/set_as_current";
    const response = await axios.get(prependPath(url), { params: { id: historyId } });
    return doResponse(response);
}

/**
 * Get list of histories from server and return them.
 * @return {Promise.<Array>} list of histories
 */
export async function getHistoryList() {
    const url = "api/histories";
    const response = await axios.get(prependPath(url), { params: stdHistoryParams });
    return doResponse(response);
}

/**
 * Load one history by id
 * @param {String} id
 */
export async function getHistoryByIdFromServer(id) {
    const path = `api/histories/${id}`;
    const response = await axios.get(prependPath(path), { params: extendedHistoryParams });
    return doResponse(response);
}

/**
 * Set permissions to private for indicated history
 * TODO: rewrite API endpoint for this
 * @param {Object} history the history to secure
 * @return {Object} the secured history
 */
export async function secureHistoryOnServer(history) {
    const { id } = history;
    const url = "history/make_private";
    const response = await axios.post(prependPath(url), formData({ history_id: id }));
    if (response.status !== 200) {
        throw new Error(response.statusText);
    }
    return await getHistoryByIdFromServer(id);
}

/**
 * Update specific fields in history
 * @param {Object} historyId the history id to update
 * @param {Object} payload fields to update
 * @return {Object} the updated history
 */
export async function updateHistoryFields(historyId, payload) {
    const url = `api/histories/${historyId}`;
    const response = await axios.put(prependPath(url), payload, { params: extendedHistoryParams });
    return doResponse(response);
}
