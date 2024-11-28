import { defineStore } from "pinia";
import { ref } from "vue";

import { GalaxyApi } from "@/api";
import { type InvocationJobsSummary, type InvocationStep, type WorkflowInvocation } from "@/api/invocations";
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

    async function fetchInvocationStep(params: FetchParams): Promise<InvocationStep> {
        const { data, error } = await GalaxyApi().GET("/api/invocations/steps/{step_id}", {
            params: { path: { step_id: params.id } },
        });
        if (error) {
            rethrowSimple(error);
        }
        return data;
    }

    const { getItemById: getInvocationById, fetchItemById: fetchInvocationForId } =
        useKeyedCache<WorkflowInvocation>(fetchInvocationDetails);

    const { getItemById: getInvocationJobsSummaryById, fetchItemById: fetchInvocationJobsSummaryForId } =
        useKeyedCache<InvocationJobsSummary>(fetchInvocationJobsSummary);

    const { getItemById: getInvocationStepById, fetchItemById: fetchInvocationStepById } =
        useKeyedCache<InvocationStep>(fetchInvocationStep);

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
