import axios from "axios";

import { updateWorkflow, type WorkflowSummary } from "@/api/workflows";
import { getAppRoot } from "@/onload/loadConfig";
import { errorMessageAsString, rethrowSimple } from "@/utils/simple-error";

import { toSimple, type Workflow } from "./model";

/** Workflow data request helper **/
export async function getVersions(id: string) {
    try {
        const { data } = await axios.get(`${getAppRoot()}api/workflows/${id}/versions`);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

export async function getModule(
    request_data: Record<string, any>,
    stepId: number,
    setLoadingState: (stepId: number, loading: boolean, error?: string) => void
) {
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

export async function refactor(id: string, actions: Record<string, any>, dryRun = false) {
    try {
        const requestData = {
            actions: actions,
            style: "editor",
            dry_run: dryRun,
        };
        const { data } = await axios.put(`${getAppRoot()}api/workflows/${id}/refactor`, requestData);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

export async function loadWorkflow({ id, version = null }: { id: string; version?: number | null }) {
    try {
        const versionQuery = Number.isInteger(version) ? `version=${version}` : "";
        const { data } = await axios.get(`${getAppRoot()}workflow/load_workflow?_=true&id=${id}&${versionQuery}`);
        return data;
    } catch (e) {
        console.debug(e);
        rethrowSimple(e);
    }
}

// TODO: The backend return will be typed as the update response
type WorkflowSummaryExtended = WorkflowSummary & {
    version: number;
    annotation: string;
};
export async function saveWorkflow(workflow: Record<string, any>) {
    if (workflow.hasChanges) {
        try {
            const requestData = { ...toSimple(workflow.id, workflow as Workflow), from_tool_form: true };
            const data = (await updateWorkflow(workflow.id, requestData)) as WorkflowSummaryExtended;
            workflow.name = data.name;
            workflow.hasChanges = false;
            workflow.stored = true;
            workflow.version = data.version;
            if (workflow.annotation || data.annotation) {
                workflow.annotation = data.annotation;
            }
            return data;
        } catch (e) {
            rethrowSimple(e);
        }
    }
    return {};
}

export async function getToolPredictions(requestData: Record<string, any>) {
    try {
        const { data } = await axios.post(`${getAppRoot()}api/workflows/get_tool_predictions`, requestData);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}
