import { defineStore } from "pinia";

import { client } from "@/api";
import {
    fetchInvocationJobsSummary,
    fetchInvocationStep,
    type WorkflowInvocation,
    type WorkflowInvocationJobsSummary,
    type WorkflowInvocationStep,
} from "@/api/invocations";
import { type FetchParams, useKeyedCache } from "@/composables/keyedCache";
import { rethrowSimple } from "@/utils/simple-error";

export const useInvocationStore = defineStore("invocationStore", () => {
    async function fetchInvocationDetails(params: FetchParams): Promise<WorkflowInvocation> {
        const { data, error } = await client.GET("/api/invocations/{invocation_id}", {
            params: { path: { invocation_id: params.id } },
        });
        if (error) {
            rethrowSimple(error);
        }
        return data;
    }

    const { getItemById: getInvocationById, fetchItemById: fetchInvocationForId } =
        useKeyedCache<WorkflowInvocation>(fetchInvocationDetails);

    const { getItemById: getInvocationJobsSummaryById, fetchItemById: fetchInvocationJobsSummaryForId } =
        useKeyedCache<WorkflowInvocationJobsSummary>(fetchInvocationJobsSummary);

    const { getItemById: getInvocationStepById, fetchItemById: fetchInvocationStepById } =
        useKeyedCache<WorkflowInvocationStep>(fetchInvocationStep);

    return {
        getInvocationById,
        fetchInvocationForId,
        getInvocationJobsSummaryById,
        fetchInvocationJobsSummaryForId,
        getInvocationStepById,
        fetchInvocationStepById,
    };
});
