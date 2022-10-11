import axios from "axios";
import { rethrowSimple } from "utils/simple-error";
import { getAppRoot } from "onload/loadConfig";

export async function updateToolFormData(tool_id, tool_version, history_id, inputs) {
    const current_state = {
        tool_id: tool_id,
        tool_version: tool_version,
        inputs: inputs,
        history_id: history_id,
    };
    const url = `${getAppRoot()}api/tools/${tool_id}/build`;
    try {
        const { data } = await axios.post(url, current_state);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

/** Tools data request helper **/
export async function getToolFormData(tool_id, tool_version, job_id, history_id) {
    let url = "";
    const data = {};

    // build request url and collect request data
    if (job_id) {
        url = `${getAppRoot()}api/jobs/${job_id}/build_for_rerun`;
    } else {
        url = `${getAppRoot()}api/tools/${tool_id}/build`;
        const queryString = window.location.search;
        const params = new URLSearchParams(queryString);
        for (const [key, value] of params.entries()) {
            if (key != "tool_id") {
                data[key] = value;
            }
        }
    }
    history_id && (data["history_id"] = history_id);
    tool_version && (data["tool_version"] = tool_version);

    // attach data to request url
    if (Object.entries(data).length != 0) {
        const params = new URLSearchParams(data);
        url = `${url}?${params.toString()}`;
    }

    // request tool data
    try {
        const { data } = await axios.get(url);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

export async function submitJob(jobDetails) {
    const url = `${getAppRoot()}api/tools`;
    const { data } = await axios.post(url, jobDetails);
    return data;
}
