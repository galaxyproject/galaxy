import { getAppRoot } from "onload/loadConfig";
import axios from "axios";

export function getDisplayApplications() {
    let url = `${getAppRoot()}api/display_applications`;
    return axios.get(url);
}

export function reloadDisplayApplications(ids) {
    let url = `${getAppRoot()}api/display_applications/reload`;
    return axios.post(url, { ids: ids });
}
