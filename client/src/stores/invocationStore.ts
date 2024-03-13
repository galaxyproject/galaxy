import { defineStore } from "pinia";

import {
    fetchInvocationDetails,
    fetchInvocationJobsSummary,
    fetchInvocationStep,
    type InvocationJobsSummary,
    type WorkflowInvocation,
    type WorkflowInvocationStep,
} from "@/api/invocations";
import { useKeyedCache } from "@/composables/keyedCache";

export const useInvocationStore = defineStore("invocationStore", () => {
    const { getItemById: getInvocationById, fetchItemById: fetchInvocationForId } =
        useKeyedCache<WorkflowInvocation>(fetchInvocationDetails);

    const { getItemById: getInvocationJobsSummaryById, fetchItemById: fetchInvocationJobsSummaryForId } =
        useKeyedCache<InvocationJobsSummary>(fetchInvocationJobsSummary);

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
