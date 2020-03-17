import axios from "axios";
import { rethrowSimple } from "utils/simple-error";
import { getAppRoot } from "onload/loadConfig";

/** Workflow data request helper **/
export async function getVersions(id) {
    try {
        const response = await axios.get(`${getAppRoot()}api/workflows/${id}/versions`);
        return response.data;
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
        const response = await axios.post(`${getAppRoot()}api/workflows/build_module`, request_data);
        return response.data;
    } catch (e) {
        rethrowSimple(e);
    }
}

export async function loadWorkflow(workflow, id, version) {
    try {
        const versionQuery = version ? `version=${version}` : "";
        const { data } = await axios.get(`${getAppRoot()}workflow/load_workflow?_=true&id=${id}&${versionQuery}`);
        workflow.remove_all();
        workflow.from_simple(data, true);
        workflow.has_changes = false;
        workflow.fit_canvas_to_nodes();
        workflow.scroll_to_nodes();
        workflow.canvas_manager.draw_overview();
        return data;
    } catch (e) {
        console.debug(e);
        rethrowSimple(e);
    }
}

export async function saveWorkflow(workflow, id) {
    workflow.rectify_workflow_outputs();
    if (workflow.has_changes) {
        try {
            const requestData = { workflow: workflow.to_simple(), from_tool_form: true };
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
