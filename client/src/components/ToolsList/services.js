import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { rethrowSimple } from "utils/simple-error";

export async function fetchData(url) {
    try {
        const { data } = await axios.get(`${getAppRoot()}${url}`);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}
