import axios from "axios";
import { rethrowSimple } from "utils/simple-error";
import { getAppRoot } from "onload/loadConfig";

export async function submitData(url, payload) {
    try {
        const { data } = await axios.put(`${getAppRoot()}${url}`, payload);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}
