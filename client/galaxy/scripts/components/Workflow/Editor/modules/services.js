import axios from "axios";
import { rethrowSimple } from "utils/simple-error";
import { getAppRoot } from "onload/loadConfig";

/** Workflow data request helper **/
export async function getVersions(id) {
    try {
        const { data } = await axios.get(`${getAppRoot()}api/workflows/${id}/versions`);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

export async function getDatatypes() {
    try {
        const datatypesRequest = await axios.get(`${getAppRoot()}api/datatypes`);
        const datatypes = datatypesRequest.data;
        const mappingRequest = await axios.get(`${getAppRoot()}api/datatypes/mapping`);
        const datatypes_mapping = mappingRequest.data;
        return { datatypes, datatypes_mapping };
    } catch (e) {
        rethrowSimple(e);
    }
}

export async function getModule(request_data) {
    try {
        const { data } = await axios.post(`${getAppRoot()}api/workflows/build_module`, request_data);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

export async function loadWorkflow(workflow, id, version, appendData) {
    try {
        const versionQuery = version ? `version=${version}` : "";
        const { data } = await axios.get(`${getAppRoot()}workflow/load_workflow?_=true&id=${id}&${versionQuery}`);
        workflow.fromSimple(data, appendData);
        return data;
    } catch (e) {
        console.debug(e);
        rethrowSimple(e);
    }
}

export async function saveWorkflow(workflow, id) {
    if (workflow.has_changes) {
        try {
            const requestData = { workflow: workflow.toSimple(), from_tool_form: true };
            const { data } = await axios.put(`${getAppRoot()}api/workflows/${id}`, requestData);
            workflow.name = data.name;
            workflow.has_changes = false;
            workflow.stored = true;
            workflow.workflow_version = data.version;
            return data;
        } catch (e) {
            rethrowSimple(e);
        }
    }
    return {};
}

export async function getDatatypeMapping() {
    try {
        const { data } = await axios.get(`${getAppRoot()}api/datatypes/mapping`);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

export async function getToolPredictions(requestData) {
    try {
        const { data } = await axios.post(`${getAppRoot()}api/workflows/get_tool_predictions`, requestData);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}
