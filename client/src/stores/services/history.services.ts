import axios, { type AxiosResponse } from "axios";

import type { AnyHistory } from "@/api";
import { prependPath } from "@/utils/redirect";

/**
 * Generic json getter
 * @param response
 * @return response.data or throws an error if response status is not 200
 */
function doResponse(response: AxiosResponse) {
    if (response.status !== 200) {
        throw new Error(response.statusText);
    }
    return response.data;
}

/**
 * Some current endpoints don't accept JSON, so we need to
 * do some massaging to send in old form post data.
 */
function formData(fields = {} as Record<string, any>) {
    return Object.keys(fields).reduce((result, fieldName) => {
        result.set(fieldName, fields[fieldName]);
        return result;
    }, new FormData());
}

/** Default history request parameters. */
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
 * @return the new history or throws an error if new history creation fails
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
 * @param history Source history
 * @param name New history name
 * @param copyAll Copy existing contents
 */
export async function cloneHistory(history: AnyHistory, name: string, copyAll: boolean) {
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
 * Get current history from server and return it.
 * @param since timestamp to get histories since
 * @return the current history
 */
export async function getCurrentHistoryFromServer(since: string | undefined = undefined) {
    const url = "history/current_history_json";
    const response = await axios.get(prependPath(url), { params: { since: since } });
    return doResponse(response);
}

/**
 * Set current history on server and return it.
 * @param historyId Encoded history id
 * @return the current history
 */
export async function setCurrentHistoryOnServer(historyId: string) {
    const url = "history/set_as_current";
    const response = await axios.get(prependPath(url), { params: { id: historyId } });
    return doResponse(response);
}

/**
 * Get list of histories from server and return them.
 * @param offset to start from (default = 0)
 * @param limit of histories to load (default = null; in which case no limit)
 * @param queryString to append to url in the form `q=filter&qv=val&q=...`
 * @return list of histories
 */
export async function getHistoryList(offset = 0, limit: number | null = null, queryString = "") {
    const params = `view=summary&order=update_time&offset=${offset}`;
    let url = `api/histories?${params}`;
    if (limit !== null) {
        url += `&limit=${limit}`;
    }
    if (queryString !== "") {
        url += `&${queryString}`;
    }
    const response = await axios.get(prependPath(url));
    return doResponse(response);
}

/**
 * Get number of histories for current user from server and return them.
 * @return number of histories
 */
export async function getHistoryCount() {
    // This url is temp. for this PR, waiting on:
    // https://github.com/galaxyproject/galaxy/pull/16075
    const url = "api/histories/count";
    const response = await axios.get(prependPath(url));
    return doResponse(response);
}

/** Load one history by id */
export async function getHistoryByIdFromServer(id: string) {
    const path = `api/histories/${id}`;
    const response = await axios.get(prependPath(path), { params: extendedHistoryParams });
    return doResponse(response);
}

/**
 * Set permissions to private for indicated history
 * TODO: rewrite API endpoint for this
 * @param history the history to secure
 * @return the secured history
 */
export async function secureHistoryOnServer(history: AnyHistory) {
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
 * @param historyId the history id to update
 * @param payload fields to update
 * @return the updated history
 */
export async function updateHistoryFields(historyId: string, payload: Record<string, any>) {
    const url = `api/histories/${historyId}`;
    const response = await axios.put(prependPath(url), payload, { params: extendedHistoryParams });
    return doResponse(response);
}
