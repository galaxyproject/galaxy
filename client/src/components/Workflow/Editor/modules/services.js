import axios from "axios";

import { getAppRoot } from "@/onload/loadConfig";
import { errorMessageAsString, rethrowSimple } from "@/utils/simple-error";

import { toSimple } from "./model";

/** Workflow data request helper **/
export async function getVersions(id) {
    try {
        const { data } = await axios.get(`${getAppRoot()}api/workflows/${id}/versions`);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

export async function getModule(request_data, stepId, setLoadingState) {
    setLoadingState(stepId, true);
    try {
        const { data } = await axios.post(`${getAppRoot()}api/workflows/build_module`, request_data);
        setLoadingState(stepId, false);
        return data;
    } catch (e) {
        setLoadingState(stepId, false, errorMessageAsString(e));
        rethrowSimple(e);
    }
}

export async function saveWorkflow(workflow) {
    try {
        const requestData = { workflow: toSimple(workflow.id, workflow), from_tool_form: true };
        const { data } = await axios.put(`${getAppRoot()}api/workflows/${workflow.id}`, requestData);
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
