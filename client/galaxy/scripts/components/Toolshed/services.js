import axios from "axios";
import { getAppRoot } from "onload/loadConfig";

/** Request repositories from Toolshed server **/
export class Services {
    getRepositories(params) {
        const url = `${getAppRoot()}api/tool_shed/search?${params.join("&")}`;
        return new Promise((resolve, reject) => {
            axios
                .get(url)
                .then(response => {
                    const data = response.data;
                    const incoming = data.hits.map(x => x.repository);
                    incoming.forEach(x => {

                        x.times_downloaded = this.formatCount(x.times_downloaded);
                        x.repository_url = `${data.hostname}repository?repository_id=${x.id}`;
                    });
                    resolve(incoming);
                })
                .catch(e => {
                    let errorMessage = "Request failed.";
                    if (e.response) {
                        errorMessage = e.response.data.err_msg || `${e.response.statusText} (${e.response.status})`;
                    }
                    reject(errorMessage);
                });
        });
    }

    formatCount(value) {
        if (value > 1000) return `>${Math.floor(value / 1000)}k`;
        return value;
    }
}
