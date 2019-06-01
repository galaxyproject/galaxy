import axios from "axios";
import { getAppRoot } from "onload/loadConfig";

/** Request repositories, categories etc from toolshed server **/
export class Services {
    getCategories(toolshedUrl) {
        const url = `${getAppRoot()}api/repositories/categories?tool_shed_url=${toolshedUrl}`;
        return new Promise((resolve, reject) => {
            axios
                .get(url)
                .then(response => {
                    resolve(response.data);
                })
                .catch(e => {
                    reject(this._errorMessage(e));
                });
        });
    }

    getRepositories(params) {
        const paramsString = Object.keys(params).reduce(function(previous, key) {
            return `${previous}${key}=${params[key]}&`;
        }, "");
        const url = `${getAppRoot()}api/repositories/search?${paramsString}`;
        return new Promise((resolve, reject) => {
            axios
                .get(url)
                .then(response => {
                    const data = response.data;
                    const incoming = data.hits.map(x => x.repository);
                    incoming.forEach(x => {
                        x.times_downloaded = this._formatCount(x.times_downloaded);
                        x.repository_url = `${data.hostname}repository?repository_id=${x.id}`;
                    });
                    resolve(incoming);
                })
                .catch(e => {
                    reject(this._errorMessage(e));
                });
        });
    }

    getDetails(toolshedUrl, repository_id) {
        const params = `tool_shed_url=${toolshedUrl}&repository_id=${repository_id}`;
        const url = `${getAppRoot()}api/repositories/details?${params}`;
        return new Promise((resolve, reject) => {
            axios
                .get(url)
                .then(response => {
                    const data = response.data;
                    const table = Object.keys(data).map(key => {
                        const d = data[key];
                        return {
                            numeric_revision: d.numeric_revision,
                            changeset_revision: d.changeset_revision,
                            includes_tools: d.includes_tools,
                            includes_workflows: d.includes_workflows,
                            includes_datatypes: d.includes_datatypes,
                            includes_tool_dependencies: d.includes_tool_dependencies,
                            includes_tools_for_display_in_tool_panel: d.includes_tools_for_display_in_tool_panel
                        };
                    });
                    table.sort((a,b) => a.numeric_revision < b.numeric_revision);
                    resolve(table);
                })
                .catch(e => {
                    reject(this._errorMessage(e));
                });
        });
    }

    getInstalled(repo) {
        const paramsString = `name=${repo.name}&owner=${repo.repo_owner_username}`;
        const url = `${getAppRoot()}api/repositories?${paramsString}`;
        return new Promise((resolve, reject) => {
            axios
                .get(url)
                .then(response => {
                    const data = response.data;
                    const revisions = {};
                    data.forEach(x => {
                        const installed = !x.deleted && !x.uninstalled;
                        revisions[x.changeset_revision] =
                            revisions[x.installed_changeset_revision] = installed;
                    });
                    resolve(revisions);
                })
                .catch(e => {
                    reject(this._errorMessage(e));
                });
        });
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

    installRepository(payload) {
        const url = `${getAppRoot()}api/repositories/install`;
        payload.shed_tool_conf = "./config/shed_tool_conf.xml";
        payload.tool_panel_section_id = "getext";
        payload.async = "True";
        return new Promise((resolve, reject) => {
            axios
                .post(url, payload)
                .then(response => {
                    resolve(response.data);
                })
                .catch(e => {
                    window.console.log(e);
                    reject(this._errorMessage(e));
                });
        });
    }

    uninstallRepository(payload) {
        const url = `${getAppRoot()}api/repositories/uninstall`;
        return new Promise((resolve, reject) => {
            axios
                .delete(url, { data: payload })
                .then(response => {
                    resolve(response.data);
                })
                .catch(e => {
                    window.console.log(e);
                    reject(this._errorMessage(e));
                });
        });
    }
}
