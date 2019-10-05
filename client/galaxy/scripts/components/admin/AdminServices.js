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

export function getActiveInvocations() {
    const params = { include_terminal: "false" };
    const url = `${getAppRoot()}api/invocations`;
    return axios.get(url, { params: params });
}

export function getInstalledRepositories() {
    const url = `${getAppRoot()}api/tool_shed_repositories?uninstalled=False`;
    return axios.get(url);
}

export function resetRepositoryMetadata(repository_ids) {
    const url = `${getAppRoot()}api/tool_shed_repositories/reset_metadata_on_selected_installed_repositories?repository_ids=${repository_ids}`;
    return axios.post(url);
}
