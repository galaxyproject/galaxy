import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { rethrowSimple } from "utils/simple-error";

export async function urlData({ url, headers, params }) {
    try {
        console.debug("Requesting data from: ", url);
        headers = headers || {};
        params = params || {};
        const { data } = await axios.get(`${getAppRoot()}${url}`, { headers, params });
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

/**
 * Adds search parameters to url.
 *
 * @param {String} original url
 * @param {Object} params which will be added to the url
 * @returns
 */
export function addSearchParams(url, params) {
    const placeholder = url.indexOf("?") == -1 ? "?" : "&";
    const searchParams = new URLSearchParams(params);
    const searchString = searchParams.toString();
    return searchString ? `${url}${placeholder}${searchString}` : url;
}
