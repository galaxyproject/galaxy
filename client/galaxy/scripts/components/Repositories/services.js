import axios from "axios";
import { getGalaxyInstance } from "app";

/** Workflow data request helper **/
export class Services {
    constructor(options = {}) {
        this.root = options.root;
    }
    async getInstalledRepositories() {
        const Galaxy = getGalaxyInstance();
        const url = `${this.root}api/tool_shed_repositories/?deleted=false&uninstalled=false`;
        try {
            const response = await axios.get(url);
            const incoming = response.data;
            const repositories = [];
            const hash = {};
            incoming.forEach(x => {
                const hashCode = `${x.name}_${x.owner}`;
                if (!hash[hashCode]) {
                    hash[hashCode] = true;
                    for (const url of Galaxy.config.tool_shed_urls) {
                        if (url.includes(x.tool_shed)) {
                            x.tool_shed_url = url;
                            break;
                        }
                    }
                    repositories.push(x);
                }
            });
            return repositories;
        } catch (e) {
            this._errorMessage(e);
        }
    }
    async getRepository(repository) {
        const params = `tool_shed_url=${repository.tool_shed_url}&name=${repository.name}&owner=${repository.owner}`;
        const url = `${this.root}api/tool_shed/request?controller=repositories&${params}`;
        try {
            const response = await axios.get(url);
            const length = response.data.length;
            if (length > 0) {
                const result = response.data[0];
                result.repository_url = `${repository.tool_shed_url}repository?repository_id=${result.id}`;
                return result;
            } else {
                throw "Repository details not found.";
            }
        } catch (e) {
            this._errorMessage(e);
        }
    }
    _errorMessage(e) {
        let message = "Request failed.";
        if (e.response) {
            message = e.response.data.err_msg || `${e.response.statusText} (${e.response.status})`;
        } else if (typeof e == "string") {
            message = e;
        }
        throw message;
    }
}
