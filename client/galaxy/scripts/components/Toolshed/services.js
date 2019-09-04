import axios from "axios";
import { getAppRoot } from "onload/loadConfig";

/** Request repositories, categories etc from toolshed server **/
export class Services {
    async getCategories(toolshedUrl) {
        const paramString = `tool_shed_url=${toolshedUrl}&controller=categories`;
        const url = `${getAppRoot()}api/tool_shed/request?${paramString}`;
        try {
            const response = await axios.get(url);
            return response.data;
        } catch (e) {
            return this._errorMessage(e);
        }
    }
    async getRepositories(params) {
        params["controller"] = "repositories";
        const paramString = this._getParamString(params);
        const url = `${getAppRoot()}api/tool_shed/request?${paramString}`;
        try {
            const response = await axios.get(url);
            const data = response.data;
            const incoming = data.hits.map(x => x.repository);
            incoming.forEach(x => {
                x.times_downloaded = this._formatCount(x.times_downloaded);
                x.repository_url = `${data.hostname}repository?repository_id=${x.id}`;
            });
            return incoming;
        } catch (e) {
            return this._errorMessage(e);
        }
    }
    async getDetails(toolshedUrl, repository_id) {
        const paramString = `tool_shed_url=${toolshedUrl}&id=${repository_id}&controller=repositories&action=metadata`;
        const url = `${getAppRoot()}api/tool_shed/request?${paramString}`;
        try {
            const response = await axios.get(url);
            const data = response.data;
            const table = Object.keys(data).map(key => data[key]);
            table.sort((a, b) => b.numeric_revision - a.numeric_revision);
            table.forEach(x => {
                if (Array.isArray(x.tools)) {
                    x.profile = x.tools.reduce(
                        (value, current) => (current.profile > value ? current.profile : value),
                        null
                    );
                }
            });
            return table;
        } catch (e) {
            return `${this._errorMessage(e)}, ${url}`;
        }
    }
    async getInstalledRepositories(repo) {
        const paramsString = `name=${repo.name}&owner=${repo.repo_owner_username}`;
        const url = `${getAppRoot()}api/tool_shed_repositories?${paramsString}`;
        try {
            const response = await axios.get(url);
            const data = response.data;
            const result = {};
            data.forEach(x => {
                const d = {
                    status: x.status,
                    installed: !x.deleted && !x.uninstalled
                };
                result[x.changeset_revision] = result[x.installed_changeset_revision] = d;
            });
            return result;
        } catch (e) {
            this._errorMessage(e);
        }
    }
    async installRepository(payload) {
        const url = `${getAppRoot()}api/tool_shed_repositories`;
        try {
            const response = await axios.post(url, payload);
            return response.data;
        } catch (e) {
            return this._errorMessage(e);
        }
    }
    async uninstallRepository(params) {
        const paramsString = Object.keys(params).reduce(function(previous, key) {
            return `${previous}${key}=${params[key]}&`;
        }, "");
        const url = `${getAppRoot()}api/tool_shed_repositories?${paramsString}`;
        try {
            const response = await axios.delete(url);
            return response.data;
        } catch (e) {
            return this._errorMessage(e);
        }
    }
    _formatCount(value) {
        if (value > 1000) return `>${Math.floor(value / 1000)}k`;
        return value;
    }
    _errorMessage(e) {
        let message = "Request failed.";
        if (e.response) {
            message = e.response.data.err_msg || `${e.response.statusText} (${e.response.status})`;
        }
        return message;
    }
    _getParamString(params) {
        return Object.keys(params).reduce(function(previous, key) {
            return `${previous}${key}=${params[key]}&`;
        }, "");
    }
}
