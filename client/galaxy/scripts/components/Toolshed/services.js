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
                    reject(this.errorMessage(e));
                });
        });
    }

    getRepositories(params) {
        const paramsString = Object.keys(params).reduce(function (previous, key) {
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
                        x.times_downloaded = this.formatCount(x.times_downloaded);
                        x.repository_url = `${data.hostname}repository?repository_id=${x.id}`;
                    });
                    resolve(incoming);
                })
                .catch(e => {
                    reject(this.errorMessage(e));
                });
        });
    }

    formatCount(value) {
        if (value > 1000) return `>${Math.floor(value / 1000)}k`;
        return value;
    }

    errorMessage(e) {
        let message = "Request failed.";
        if (e.response) {
            message = e.response.data.err_msg || `${e.response.statusText} (${e.response.status})`;
        }
        return message;
    }

    addInstalledStates(metadata) {
        /*var params = { name: metadata.name, owner: metadata.owner };
        var already_installed = false;
        $.get(`${getAppRoot()}api/tool_shed_repositories`, params, data => {
            for (var index = 0; index < data.length; index++) {
                var repository = data[index];
                var installed = !repository.deleted && !repository.uninstalled;
                var changeset_match =
                    repository.changeset_revision == metadata.changeset_revision ||
                    repository.installed_changeset_revision == metadata.changeset_revision;
                if (
                    repository.name == metadata.name &&
                    repository.owner == metadata.owner &&
                    installed &&
                    changeset_match
                ) {
                    already_installed = true;
                }
                if (already_installed) {
                    $("#install_repository").prop("disabled", true);
                    $("#install_repository").val("This revision is already installed");
                } else {
                    $("#install_repository").prop("disabled", false);
                    $("#install_repository").val("Install this revision");
                }
            }
            if (this.repoQueued(metadata) || already_installed) {
                $("#queue_install").hide();
                $("#queue_install").val("This revision is already in the queue");
            } else {
                $("#queue_install").show();
                $("#queue_install").val("Install this revision later");
            }
        });*/
    }
}
