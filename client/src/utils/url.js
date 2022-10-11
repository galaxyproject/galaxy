import axios from "axios";
import { safePath } from "utils/redirect";
import { rethrowSimple } from "utils/simple-error";

export async function urlData({ url, headers, params }) {
    try {
        console.debug("Requesting data from: ", url);
        headers = headers || {};
        params = params || {};
        const { data } = await axios.get(safePath(url), { headers, params });
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}
