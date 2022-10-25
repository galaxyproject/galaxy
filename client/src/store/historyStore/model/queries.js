/**
 * Simple ajax queries that run against the api.
 *
 * A few history queries still hit routes that don't begin with /api. I have noted them
 * in the comments.
 */

import axios from "axios";
import { prependPath } from "utils/redirect";

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

/**
 * Default history request parameters
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
 * Return list of available histories
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
export async function getHistoryById(id) {
    const path = `api/histories/${id}`;
    const response = await axios.get(prependPath(path), { params: extendedHistoryParams });
    return doResponse(response);
}

/**
 * Create new history
 */
export async function createNewHistory() {
    // TODO: adjust api, keep this for later
    // const url = `api/histories`;
    // const data = Object.assign({ name: "New History" }, props);
    // const response = await axios.post(prependPath(url), data, { params: stdHistoryParams });

    // using old route to create and select new history at same time
    const url = "history/create_new_current";
    const createResponse = await axios.get(prependPath(url));
    const id = createResponse?.data?.id || null;
    if (!id) {
        throw new Error("failed to create and select new history");
    }
    return doResponse(createResponse);
}

/**
 * Generates copy of history on server
 * @param {Object} history Source history
 * @param {String} name New history name
 * @param {Boolean} copyAll Copy existing contents
 */
export async function cloneHistory(history, name, copyAll) {
    const url = `api/histories`;
    const payload = {
        history_id: history.id,
        name,
        all_datasets: copyAll,
        current: true,
    };
    const response = await axios.post(prependPath(url), payload, { params: stdHistoryParams });
    return doResponse(response);
}

/**
 * Delete history on server
 * @param {String} id Encoded history id
 * @param {Boolean} purge Permanent delete
 */
export async function deleteHistoryById(id, purge = false) {
    const url = `api/histories/${id}` + (purge ? "?purge=True" : "");
    const response = await axios.delete(prependPath(url), { params: stdHistoryParams });
    return doResponse(response);
}

/**
 * Update specific fields in history
 * @param {Object} history
 * @param {Object} payload fields to update
 */
export async function updateHistoryFields(id, payload) {
    const url = `api/histories/${id}`;
    const response = await axios.put(prependPath(url), payload, { params: extendedHistoryParams });
    return doResponse(response);
}

/**
 * Set permissions to private for indicated history
 * TODO: rewrite API endpoint for this
 * @param {String} history_id
 */
export async function secureHistory(history) {
    const { id } = history;
    const url = "history/make_private";
    const response = await axios.post(prependPath(url), formData({ history_id: id }));
    if (response.status != 200) {
        throw new Error(response);
    }
    return await getHistoryById(id);
}

/**
 * Content Current History
 */
export async function getCurrentHistoryFromServer(since) {
    const url = "history/current_history_json";
    const response = await axios.get(prependPath(url), { params: { since: since } });
    return doResponse(response);
}

export async function setCurrentHistoryOnServer(history_id) {
    const url = "history/set_as_current";
    const response = await axios.get(prependPath(url), {
        params: { id: history_id },
    });
    return doResponse(response);
}
