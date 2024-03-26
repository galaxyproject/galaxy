import { defineStore } from "pinia";

import {
    fetchInvocationDetails,
    fetchInvocationStepStateDetails,
    fetchInvocationJobsSummary,
    fetchInvocationStep,
    type WorkflowInvocation,
    type InvocationJobsSummary,
    type WorkflowInvocationStep,
} from "@/api/invocations";
import { useKeyedCache } from "@/composables/keyedCache";

export const useInvocationStore = defineStore("invocationStore", () => {
    const { getItemById: getInvocationById, fetchItemById: fetchInvocationForId } =
        useKeyedCache<WorkflowInvocation>(fetchInvocationDetails);

    const { getItemById: getInvocationWithStepStatesById, fetchItemById: fetchInvocationWithStepStatesForId } =
        useKeyedCache<WorkflowInvocation>(fetchInvocationStepStateDetails);

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
        getInvocationWithStepStatesById,
        fetchInvocationWithStepStatesForId,
    };
});
