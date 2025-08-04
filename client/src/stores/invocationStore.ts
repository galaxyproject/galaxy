import { defineStore } from "pinia";
import { ref, set } from "vue";

import { GalaxyApi } from "@/api";
import type {
    InvocationJobsSummary,
    InvocationStep,
    StepJobSummary,
    WorkflowInvocation,
    WorkflowInvocationRequest,
} from "@/api/invocations";
import { type FetchParams, useKeyedCache } from "@/composables/keyedCache";
import type { GraphStep } from "@/composables/useInvocationGraph";
import { rethrowSimple } from "@/utils/simple-error";

type GraphSteps = { [index: string]: GraphStep };

export const useInvocationStore = defineStore("invocationStore", () => {
    const graphStepsByStoreId = ref<{ [index: string]: GraphSteps }>({});

    async function fetchInvocationDetails(params: FetchParams): Promise<WorkflowInvocation> {
        const { data, error } = await GalaxyApi().GET("/api/invocations/{invocation_id}", {
            params: { path: { invocation_id: params.id } },
        });
        if (error) {
            rethrowSimple(error);
        }
        return data;
    }

    async function fetchInvocationJobsSummary(params: FetchParams): Promise<InvocationJobsSummary> {
        const { data, error } = await GalaxyApi().GET("/api/invocations/{invocation_id}/jobs_summary", {
            params: { path: { invocation_id: params.id } },
        });
        if (error) {
            rethrowSimple(error);
        }
        return data;
    }

    async function fetchInvocationStepJobsSummary(params: FetchParams): Promise<StepJobSummary[]> {
        const { data, error } = await GalaxyApi().GET("/api/invocations/{invocation_id}/step_jobs_summary", {
            params: { path: { invocation_id: params.id } },
        });
        if (error) {
            rethrowSimple(error);
        }
        return data;
    }

    async function fetchInvocationStep(params: FetchParams): Promise<InvocationStep> {
        const { data, error } = await GalaxyApi().GET("/api/invocations/steps/{step_id}", {
            params: { path: { step_id: params.id } },
        });
        if (error) {
            rethrowSimple(error);
        }
        return data;
    }

    async function fetchInvocationRequest(params: FetchParams): Promise<WorkflowInvocationRequest> {
        const { data, error } = await GalaxyApi().GET("/api/invocations/{invocation_id}/request", {
            params: {
                path: {
                    invocation_id: params.id,
                },
            },
        });
        if (error) {
            rethrowSimple(error);
        }
        return data;
    }

    async function cancelWorkflowScheduling(invocationId: string) {
        const { data, error } = await GalaxyApi().DELETE("/api/invocations/{invocation_id}", {
            params: {
                path: { invocation_id: invocationId },
            },
        });
        if (error) {
            rethrowSimple(error);
        }
        storedInvocations.value[invocationId] = data;
        return data;
    }

    function updateInvocation(id: string, updatedData: Partial<WorkflowInvocation>) {
        if (storedInvocations.value[id]) {
            set(storedInvocations.value, id, {
                ...storedInvocations.value[id],
                ...updatedData,
            });
        } else {
            set(storedInvocations.value, id, updatedData);
        }
    }

    const {
        fetchItemById: fetchInvocationById,
        getItemById: getInvocationById,
        getItemLoadError: getInvocationLoadError,
        isLoadingItem: isLoadingInvocation,
        storedItems: storedInvocations,
    } = useKeyedCache<WorkflowInvocation>(fetchInvocationDetails);

    const { getItemById: getInvocationJobsSummaryById, fetchItemById: fetchInvocationJobsSummaryForId } =
        useKeyedCache<InvocationJobsSummary>(fetchInvocationJobsSummary);

    const { getItemById: getInvocationStepJobsSummaryById, fetchItemById: fetchInvocationStepJobsSummaryForId } =
        useKeyedCache<StepJobSummary[]>(fetchInvocationStepJobsSummary);

    const { getItemById: getInvocationStepById, fetchItemById: fetchInvocationStepById } =
        useKeyedCache<InvocationStep>(fetchInvocationStep);

    const { getItemById: getInvocationRequestById } = useKeyedCache<WorkflowInvocationRequest>(fetchInvocationRequest);

    return {
        cancelWorkflowScheduling,
        fetchInvocationById,
        fetchInvocationJobsSummaryForId,
        fetchInvocationStepJobsSummaryForId,
        fetchInvocationStepById,
        getInvocationById,
        getInvocationJobsSummaryById,
        getInvocationStepJobsSummaryById,
        getInvocationLoadError,
        getInvocationStepById,
        getInvocationRequestById,
        graphStepsByStoreId,
        isLoadingInvocation,
        storedInvocations,
        updateInvocation,
    };
});
