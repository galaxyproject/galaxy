import $ from "jquery";
import axios from "axios";
import { rethrowSimple } from "utils/simple-error";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";

/** Tools data request helper **/
export async function getTool(tool_id, tool_version, job_id) {
    const galaxy = getGalaxyInstance();
    let url = "";
    let data = {};

    // build request url and collect request data
    if (job_id) {
        url = `${getAppRoot()}api/jobs/${job_id}/build_for_rerun`;
    } else {
        url = `${getAppRoot()}api/tools/${tool_id}/build`;
        data = $.extend({}, galaxy.params);
        data["tool_id"] && delete data["tool_id"];
    }
    tool_version && (data["tool_version"] = tool_version);

    // attach data to request url
    if (!$.isEmptyObject(data)) {
        url += url.indexOf("?") == -1 ? "?" : "&";
        url += $.param(data, true);
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

export async function addFavorite(userId, toolId) {
    const url = `${getAppRoot()}api/users/${userId}/favorites/tools`;
    try {
        const { data } = await axios.put(url, { object_id: toolId });
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

export async function removeFavorite(userId, toolId) {
    const url = `${getAppRoot()}api/users/${userId}/favorites/tools/${encodeURIComponent(toolId)}`;
    try {
        const { data } = await axios.delete(url);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}
