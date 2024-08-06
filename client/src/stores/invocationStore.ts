import { defineStore } from "pinia";
import { ref } from "vue";

import {
    fetchInvocationDetails,
    fetchInvocationJobsSummary,
    fetchInvocationStep,
    type WorkflowInvocation,
    type WorkflowInvocationJobsSummary,
    type WorkflowInvocationStep,
} from "@/api/invocations";
import { useKeyedCache } from "@/composables/keyedCache";
import type { GraphStep } from "@/composables/useInvocationGraph";

type GraphSteps = { [index: string]: GraphStep };

export const useInvocationStore = defineStore("invocationStore", () => {
    const graphStepsByStoreId = ref<{ [index: string]: GraphSteps }>({});

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
        graphStepsByStoreId,
    };
});
