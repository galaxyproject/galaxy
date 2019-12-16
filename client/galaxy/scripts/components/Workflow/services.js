import axios from "axios";
import { getGalaxyInstance } from "app";
import { rethrowSimple } from "utils/simple-error";

/** Workflow data request helper **/
export class Services {
    constructor(options = {}) {
        this.root = options.root;
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
            workflows.forEach(workflow => {
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
        workflow.shared = workflow.owner !== Galaxy.user.get("username");
        workflow.description = "";
        if (workflow.annotations && workflow.annotations.length > 0) {
            const description = workflow.annotations[0].trim();
            if (description) {
                workflow.description = description;
            }
        }
    }
}
