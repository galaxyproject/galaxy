import { getAppRoot } from "onload/loadConfig";
import axios from "axios";

export function getErrorStack() {
    const url = `${getAppRoot()}api/tools/error_stack`;
    return axios.get(url);
}

export function getDisplayApplications() {
    const url = `${getAppRoot()}api/display_applications`;
    return axios.get(url);
}

export function reloadDisplayApplications(ids) {
    const url = `${getAppRoot()}api/display_applications/reload`;
    return axios.post(url, { ids: ids });
}
