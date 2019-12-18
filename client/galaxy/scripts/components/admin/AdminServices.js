import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
import { rethrowSimple } from "utils/simple-error";

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

export async function getDependencyUnusedPaths() {
    const params = {};
    const url = `${getAppRoot()}api/dependency_resolvers/unused_paths`;
    try {
        const response = await axios.get(url, { params: params });
        return response.data;
    } catch (e) {
        rethrowSimple(e);
    }
}

export async function deletedUnusedPaths(paths) {
    const url = `${getAppRoot()}api/dependency_resolvers/unused_paths`;
    try {
        await axios.put(url, { paths: paths });
    } catch (e) {
        rethrowSimple(e);
    }
}

export async function getToolboxDependencies(params_) {
    const params = params_ || {};
    const url = `${getAppRoot()}api/dependency_resolvers/toolbox`;
    try {
        const response = await axios.get(url, { params: params });
        return response.data;
    } catch (e) {
        rethrowSimple(e);
    }
}

export async function installDependencies(toolIds, resolutionOptions) {
    const postData = { ...resolutionOptions, tool_ids: toolIds };
    const url = `${getAppRoot()}api/dependency_resolvers/toolbox/install`;
    try {
        const response = await axios.post(url, postData);
        return response.data;
    } catch (e) {
        rethrowSimple(e);
    }
}

export async function uninstallDependencies(toolIds, resolutionOptions) {
    const postData = { ...resolutionOptions, tool_ids: toolIds };
    const url = `${getAppRoot()}api/dependency_resolvers/toolbox/uninstall`;
    try {
        const response = await axios.post(url, postData);
        return response.data;
    } catch (e) {
        rethrowSimple(e);
    }
}

export async function getContainerResolutionToolbox(params_) {
    const params = params_ || {};
    const url = `${getAppRoot()}api/container_resolvers/toolbox`;
    try {
        const response = await axios.get(url, { params: params });
        return response.data;
    } catch (e) {
        rethrowSimple(e);
    }
}

export async function resolveContainersWithInstall(toolIds, params_) {
    const data = params_ || {};
    const url = `${getAppRoot()}api/container_resolvers/toolbox/install`;
    if (toolIds && toolIds.length > 0) {
        data.tool_ids = toolIds || [];
    }
    try {
        const response = await axios.post(url, data);
        return response.data;
    } catch (e) {
        rethrowSimple(e);
    }
}
