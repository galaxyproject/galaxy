import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import { rethrowSimple } from "utils/simple-error";

/** Request repositories, categories etc from toolshed server **/
export class Services {
    async getCategories(toolshedUrl) {
        const paramsString = `tool_shed_url=${toolshedUrl}&controller=categories`;
        const url = `${getAppRoot()}api/tool_shed/request?${paramsString}`;
        try {
            const response = await axios.get(url);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }
    async getRepositories(params) {
        const paramsString = this._getParamsString(params);
        const url = `${getAppRoot()}api/tool_shed/request?controller=repositories&${paramsString}`;
        try {
            const response = await axios.get(url);
            const data = response.data;
            const incoming = data.hits.map((x) => x.repository);
            incoming.forEach((x) => {
                x.owner = x.repo_owner_username;
                x.times_downloaded = this._formatCount(x.times_downloaded);
                x.repository_url = `${data.hostname}repository?repository_id=${x.id}`;
            });
            return incoming;
        } catch (e) {
            rethrowSimple(e);
        }
    }
    async getRepository(toolshedUrl, repositoryId) {
        const paramsString = `tool_shed_url=${toolshedUrl}&id=${repositoryId}&controller=repositories&action=metadata`;
        const url = `${getAppRoot()}api/tool_shed/request?${paramsString}`;
        try {
            const response = await axios.get(url);
            const data = response.data;
            const table = Object.keys(data).map((key) => data[key]);
            if (table.length === 0) {
                throw "Repository does not contain any installable revisions.";
            }
            table.sort((a, b) => b.numeric_revision - a.numeric_revision);
            table.forEach((x) => {
                if (Array.isArray(x.tools)) {
                    x.profile = x.tools.reduce(
                        (value, current) => (current.profile > value ? current.profile : value),
                        null
                    );
                }
            });
            return table;
        } catch (e) {
            rethrowSimple(e);
        }
    }
    async getRepositoryByName(toolshedUrl, repositoryName, repositoryOwner) {
        const params = `tool_shed_url=${toolshedUrl}&name=${repositoryName}&owner=${repositoryOwner}`;
        const url = `${getAppRoot()}api/tool_shed/request?controller=repositories&${params}`;
        try {
            const response = await axios.get(url);
            const length = response.data.length;
            if (length > 0) {
                const result = response.data[0];
                result.repository_url = `${toolshedUrl}repository?repository_id=${result.id}`;
                return result;
            } else {
                throw "Repository details not found.";
            }
        } catch (e) {
            rethrowSimple(e);
        }
    }
    async getInstalledRepositories(options = {}) {
        const Galaxy = getGalaxyInstance();
        const url = `${getAppRoot()}api/tool_shed_repositories/?uninstalled=False`;
        try {
            const response = await axios.get(url);
            const repositories = this._groupByNameOwnerToolshed(response.data, options.filter, options.selectLatest);
            this._fixToolshedUrls(repositories, Galaxy.config.tool_shed_urls);
            return repositories;
        } catch (e) {
            rethrowSimple(e);
        }
    }
    async getInstalledRepositoriesByName(repositoryName, repositoryOwner) {
        const paramsString = `name=${repositoryName}&owner=${repositoryOwner}`;
        const url = `${getAppRoot()}api/tool_shed_repositories?${paramsString}`;
        try {
            const response = await axios.get(url);
            const data = response.data;
            const result = {};
            data.forEach((x) => {
                const d = {
                    status: x.status,
                    installed: !x.deleted && !x.uninstalled,
                };
                result[x.changeset_revision] = result[x.installed_changeset_revision] = d;
            });
            return result;
        } catch (e) {
            rethrowSimple(e);
        }
    }
    async installRepository(payload) {
        const url = `${getAppRoot()}api/tool_shed_repositories`;
        try {
            const response = await axios.post(url, payload);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }
    async uninstallRepository(params) {
        const paramsString = Object.keys(params).reduce(function (previous, key) {
            return `${previous}${key}=${params[key]}&`;
        }, "");
        const url = `${getAppRoot()}api/tool_shed_repositories?${paramsString}`;
        try {
            const response = await axios.delete(url);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }
    _groupByNameOwnerToolshed(incoming, filter, selectLatest) {
        if (selectLatest) {
            const getSortValue = (x, y) => {
                return x === y ? 0 : x < y ? -1 : 1;
            };
            incoming = incoming.sort((a, b) => {
                return (
                    getSortValue(a.name, b.name) ||
                    getSortValue(a.owner, b.owner) ||
                    getSortValue(a.tool_shed, b.tool_shed) ||
                    getSortValue(parseInt(b.ctx_rev), parseInt(a.ctx_rev))
                );
            });
        }
        const hash = {};
        const repositories = [];
        incoming.forEach((x) => {
            const hashCode = `${x.name}_${x.owner}_${x.tool_shed}`;
            if (!filter || filter(x)) {
                if (!hash[hashCode]) {
                    hash[hashCode] = true;
                    repositories.push(x);
                }
            }
        });
        return repositories;
    }
    _fixToolshedUrls(incoming, urls) {
        incoming.forEach((x) => {
            for (const url of urls) {
                if (url.includes(x.tool_shed)) {
                    x.tool_shed_url = url;
                    break;
                }
            }
        });
    }
    _formatCount(value) {
        if (value > 1000) {
            return `>${Math.floor(value / 1000)}k`;
        }
        return value;
    }
    _getParamsString(params) {
        if (params) {
            return Object.keys(params).reduce(function (previous, key) {
                return `${previous}${key}=${params[key]}&`;
            }, "");
        } else {
            return "";
        }
    }
}
