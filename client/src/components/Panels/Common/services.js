import axios from "axios";
import { rethrowSimple } from "utils/simple-error";
import { getAppRoot } from "onload/loadConfig";

export async function fetchData(url) {
    try {
        const { data } = await axios.get(`${getAppRoot()}${url}`);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}
