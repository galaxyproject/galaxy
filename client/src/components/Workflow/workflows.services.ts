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

    workflowData.name = `副本：${workflowData.name}`;
    const userStore = useUserStore();

    if (!userStore.matchesCurrentUsername(currentOwner)) {
        workflowData.name += ` 由用户 ${currentOwner} 分享`;
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

export async function getWorkflowFull(workflowId: string, version?: number) {
    let url = `/workflow/load_workflow?_=true&id=${workflowId}`;
    if (version !== undefined) {
        url += `&version=${version}`;
    }
    const { data } = await axios.get(withPrefix(url));
    return data;
}
