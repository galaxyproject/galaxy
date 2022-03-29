import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { rethrowSimple } from "utils/simple-error";

export async function urlData({ url }) {
    try {
        const { data } = await axios.get(`${getAppRoot()}${url}`);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

export async function urlDataWithHeaders({ url }) {
    try {
        const response = await axios.get(`${getAppRoot()}${url}`);
        return {
            data: response.data,
            headers: response.headers,
        };
    } catch (e) {
        rethrowSimple(e);
    }
}
