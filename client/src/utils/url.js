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
