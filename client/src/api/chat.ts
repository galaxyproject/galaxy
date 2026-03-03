import { rethrowSimple } from "@/utils/simple-error";

import { GalaxyApi } from "./client";

export async function generateAIInvocationReport(invocationId: string) {
    const { data, error } = await GalaxyApi().GET("/api/chat/reports/invocation/{invocation_id}", {
        params: {
            path: { invocation_id: invocationId },
        },
    });
    if (error) {
        rethrowSimple(error);
    }

    return data;
}

export async function generateAIWorkflowReport(workflowId: string, version?: number, instance?: boolean) {
    const { data, error } = await GalaxyApi().GET("/api/chat/reports/workflow/{workflow_id}", {
        params: {
            path: { workflow_id: workflowId },
            query: {
                version: version,
                instance: instance,
            },
        },
    });
    if (error) {
        rethrowSimple(error);
    }

    return data;
}
