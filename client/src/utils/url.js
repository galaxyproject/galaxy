import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { rethrowSimple } from "utils/simple-error";

export async function urlData({ url, headers }) {
    try {
        console.debug("Requesting data from: ", url);
        headers = headers || {};
        const { data } = await axios.get(`${getAppRoot()}${url}`, { headers });
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}
