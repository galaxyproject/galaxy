import axios from "axios";

import type { WorkflowSummary } from "@/api/workflows";
import { useUserStore } from "@/stores/userStore";
import { withPrefix } from "@/utils/redirect";

export async function updateWorkflow(id: string, changes: object): Promise<WorkflowSummary> {
    const { data } = await axios.put(withPrefix(`/api/workflows/${id}`), changes);
    return data;
}

export async function copyWorkflow(id: string, currentOwner?: string, version?: string): Promise<WorkflowSummary> {
    let path = `/api/workflows/${id}/download`;
    if (version) {
        path += `?version=${version}`;
    }
    const { data: workflowData } = await axios.get(withPrefix(path));

    workflowData.name = `Copy of ${workflowData.name}`;
    const userStore = useUserStore();

    if (!userStore.matchesCurrentUsername(currentOwner)) {
        workflowData.name += ` shared by user ${currentOwner}`;
    }

    const { data } = await axios.post(withPrefix("/api/workflows"), { workflow: workflowData });
    return data;
}

export async function deleteWorkflow(id: string): Promise<WorkflowSummary> {
    const { data } = await axios.delete(withPrefix(`/api/workflows/${id}`));
    return data;
}

export async function createWorkflow(workflowName: string, workflowAnnotation: string) {
    const { data } = await axios.put(withPrefix("/workflow/create"), {
        workflow_name: workflowName,
        workflow_annotation: workflowAnnotation,
    });
    return data;
}

/**
 * @param instance set when workflowId identifies a workflow revision rather than a stored
 *   workflow, which is what a subworkflow step's content_id is. Without it the id is looked
 *   up as a stored workflow and the request 404s.
 */
export async function getWorkflowFull(workflowId: string, version?: number, instance?: boolean) {
    const params: { style: string; version?: number; instance?: boolean } = { style: "editor" };
    if (Number.isInteger(version)) {
        params.version = version;
    }
    if (instance) {
        params.instance = true;
    }
    const { data } = await axios.get(withPrefix(`/api/workflows/${workflowId}/download`), { params });
    return data;
}
