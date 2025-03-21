import { getGalaxyInstance } from "app";
import axios from "axios";
import { withPrefix } from "utils/redirect";
import { rethrowSimple } from "utils/simple-error";

import { toSimple } from "./Editor/modules/model";

/** Workflow data request helper **/
export class Services {
    async copyWorkflow(workflow) {
        const Galaxy = getGalaxyInstance();
        const url = withPrefix(`/api/workflows/${workflow.id}/download`);
        try {
            const response = await axios.get(url);
            const newWorkflow = response.data;
            const currentOwner = workflow.owner;
            let newName = `${workflow.name}的副本`;
            if (currentOwner != Galaxy.user.attributes.username) {
                newName += `（由用户${currentOwner}共享）`;
            }
            newWorkflow.name = newName;
            const createUrl = withPrefix("/api/workflows");
            const createResponse = await axios.post(createUrl, { workflow: newWorkflow });
            const createWorkflow = createResponse.data;
            this._addAttributes(createWorkflow);
            return createWorkflow;
        } catch (e) {
            rethrowSimple(e);
        }
    }
    
    async createWorkflow(workflow) {
        const url = withPrefix("/api/workflows");
        try {
            const { data } = await axios.post(url, { workflow: toSimple(workflow.id, workflow), from_tool_form: true });
            return data;
        } catch (e) {
            rethrowSimple(e);
        }
    }

    async deleteWorkflow(id) {
        const url = withPrefix(`/api/workflows/${id}`);
        try {
            const response = await axios.delete(url);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }

    async undeleteWorkflow(id) {
        const url = withPrefix(`/api/workflows/${id}/undelete`);
        try {
            const response = await axios.post(url);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }

    async updateWorkflow(id, data) {
        const url = withPrefix(`/api/workflows/${id}`);
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
        const url = withPrefix("/api/trs_consume/servers");
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
        const url = withPrefix(`/api/trs_consume/${trsServer}/tools/${toolId}?tool_id_b64_encoded=true`);
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
        const url = withPrefix("/api/workflows");
        try {
            const response = await axios.post(url, data);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }

    async importTrsToolFromUrl(trsUrl) {
        const data = {
            archive_source: "trs_tool",
            trs_url: trsUrl,
        };
        const url = withPrefix("/api/workflows");
        try {
            const response = await axios.post(url, data);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }
}
