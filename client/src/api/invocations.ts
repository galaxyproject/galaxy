import { rethrowSimple } from "@/utils/simple-error";

import { GalaxyApi } from "./client";
import { type components } from "./schema";

export type WorkflowInvocationElementView = components["schemas"]["WorkflowInvocationElementView"];
export type WorkflowInvocationCollectionView = components["schemas"]["WorkflowInvocationCollectionView"];
export type InvocationJobsSummary = components["schemas"]["InvocationJobsResponse"];
export type InvocationStep = components["schemas"]["InvocationStep"];
export type InvocationMessage = components["schemas"]["InvocationMessageResponseUnion"];

export type StepJobSummary =
    | components["schemas"]["InvocationStepJobsResponseStepModel"]
    | components["schemas"]["InvocationStepJobsResponseJobModel"]
    | components["schemas"]["InvocationStepJobsResponseCollectionJobsModel"];

export type WorkflowInvocation = components["schemas"]["WorkflowInvocationResponse"];

export async function cancelWorkflowScheduling(invocationId: string) {
    const { data, error } = await GalaxyApi().DELETE("/api/invocations/{invocation_id}", {
        params: {
            path: { invocation_id: invocationId },
        },
    });
    if (error) {
        rethrowSimple(error);
    }
    return data;
}
