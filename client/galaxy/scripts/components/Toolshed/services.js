import axios from "axios";
import { getAppRoot } from "onload/loadConfig";

/** Request repositories, categories etc from toolshed server **/
export class Services {
    getCategories(toolshedUrl) {
        const url = `${getAppRoot()}api/tool_shed/categories?tool_shed_url=${toolshedUrl}`;
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
        const url = `${getAppRoot()}api/tool_shed/search?${paramsString}`;
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

    installRepository(repo) {
        window.console.log(repo);
        /*const Galaxy = getGalaxyInstance();
        const history_id = Galaxy.currHistoryPanel && Galaxy.currHistoryPanel.model.id;
        if (history_id) {
            axios
                .get(`${getAppRoot()}api/repositories/${plugin.name}?history_id=${history_id}`)
                .then(response => {
                    this.name = plugin.name;
                    this.hdas = response.data && response.data.hdas;
                    if (this.hdas && this.hdas.length > 0) {
                        this.selected = this.hdas[0].id;
                    }
                })
                .catch(e => {
                    this.error = this.setErrorMessage(e);
                });
        } else {
            this.error = "This option requires an accessible history.";
        }*/
    }

    uninstallRepository(repo) {
    }

    getInstallationState(params) {
        const paramsString = Object.keys(params).reduce(function(previous, key) {
            return `${previous}${key}=${params[key]}&`;
        }, "");
        const url = `${getAppRoot()}api/tool_shed/search?${paramsString}`;
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

    getInstalledRevisions(repo) {
        const paramsString = `name=${repo.name}&owner=${repo.owner}`;
        const url = `${getAppRoot()}api/tool_shed_repositories?${paramsString}`;
        return new Promise((resolve, reject) => {
            axios
                .get(url)
                .then(response => {
                    const data = response.data;
                    const revisions = [];
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
}
