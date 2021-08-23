import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
import { rethrowSimple } from "utils/simple-error";

export async function getEntryPoint(creating_job) {
    const params = { job_id: creating_job };
    const url = `${getAppRoot()}api/entry_points`;
    try {
        const response = await axios.get(url, { params: params });
        return response;
    } catch (e) {
        rethrowSimple(e);
    }
}
