import axios from "axios";
import { getGalaxyInstance } from "app";
import { rethrowSimple } from "utils/simple-error";
import { getAppRoot } from "onload/loadConfig";

/** Workflow data request helper **/
export class Services {
    constructor(options = {}) {
        this.root = options.root || getAppRoot();
    }

    async copyWorkflow(workflow) {
        const Galaxy = getGalaxyInstance();
        const url = `${this.root}api/workflows/${workflow.id}/download`;
        try {
            const response = await axios.get(url);
            const newWorkflow = response.data;
            const currentOwner = workflow.owner;
            let newName = `Copy of ${workflow.name}`;
            if (currentOwner != Galaxy.user.attributes.username) {
                newName += ` shared by user ${currentOwner}`;
            }
            newWorkflow.name = newName;
            const createUrl = `${this.root}api/workflows`;
            const createResponse = await axios.post(createUrl, { workflow: newWorkflow });
            const createWorkflow = createResponse.data;
            this._addAttributes(createWorkflow);
            return createWorkflow;
        } catch (e) {
            rethrowSimple(e);
        }
    }

    async deleteWorkflow(id) {
        const url = `${this.root}api/workflows/${id}`;
        try {
            const response = await axios.delete(url);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }

    async getWorkflows() {
        const url = `${this.root}api/workflows`;
        try {
            const response = await axios.get(url);
            const workflows = response.data;
            workflows.forEach((workflow) => {
                this._addAttributes(workflow);
            });
            return workflows;
        } catch (e) {
            rethrowSimple(e);
        }
    }

    async updateWorkflow(id, data) {
        const url = `${this.root}api/workflows/${id}`;
        try {
            const response = await axios.put(url, data);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }

    _addAttributes(workflow) {
        const Galaxy = getGalaxyInstance();
        workflow.shared = workflow.owner !== Galaxy.user.attributes.username;
        workflow.description = "";
        if (workflow.annotations && workflow.annotations.length > 0) {
            const description = workflow.annotations[0].trim();
            if (description) {
                workflow.description = description;
            }
        }
    }

    async getTrsServers() {
        const url = `${this.root}api/trs_consume/servers`;
        try {
            const response = await axios.get(url);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }

    async getTrsTool(trsServer, toolId) {
        // Due to the slashes in the toolId, WSGI doesn't work with
        // encodeURIComponent. I verified the framework is converting
        // the information and we're losing it. As ugly as Base64 is, it is
        // better than the alternatives IMO. -John
        // https://github.com/pallets/flask/issues/900
        toolId = btoa(toolId);
        const url = `${this.root}api/trs_consume/${trsServer}/tools/${toolId}?tool_id_b64_encoded=true`;
        try {
            const response = await axios.get(url);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }

    async importTrsTool(trsServer, toolId, versionId) {
        const data = {
            archive_source: "trs_tool",
            trs_server: trsServer,
            trs_tool_id: toolId,
            trs_version_id: versionId,
        };
        const url = `${this.root}api/workflows`;
        try {
            const response = await axios.post(url, data);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }
}

import { Observable, Subject } from "rxjs";
import { debounceTime, map } from "rxjs/operators";
import { AxiosSubscriber } from "./rxjsAxios";

export class TrsSearchService {
    constructor({ debounceInterval = 1000 }) {
        this.debounceInterval = debounceInterval;
        // Buffer for search query
        this._searchText = new Subject();
        this._trsServer = null;
    }

    get searchResults() {
        return this._searchText.pipe(
            debounceTime(this.debounceInterval),
            map((query) => {
                return [
                    query,
                    new Observable((observer) => {
                        return new AxiosSubscriber(
                            observer,
                            `${getAppRoot()}api/trs_search?query=${query}&trs_server=${this._trsServer}`
                        );
                    }),
                ];
            })
        );
    }

    set searchQuery(query) {
        this._searchText.next(query);
    }

    set trsServer(trsServer) {
        this._trsServer = trsServer;
    }
}
