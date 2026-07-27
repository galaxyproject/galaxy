import { defineStore } from "pinia";
import { computed, ref, set } from "vue";

import { GalaxyApi } from "@/api";
import type {
    InvocationJobsSummary,
    InvocationStep,
    StepJobSummary,
    WorkflowInvocation,
    WorkflowInvocationRequest,
    WorkflowJobMetric,
} from "@/api/invocations";
import { numTerminal } from "@/components/WorkflowInvocationState/util";
import { type FetchParams, useKeyedCache } from "@/composables/keyedCache";
import { rethrowSimple, rethrowSimpleWithStatus } from "@/utils/simple-error";

export const useInvocationStore = defineStore("invocationStore", () => {
    const scrollListScrollTop = ref(0);

    async function fetchInvocationDetails(params: FetchParams): Promise<WorkflowInvocation> {
        const { data, error, response } = await GalaxyApi().GET("/api/invocations/{invocation_id}", {
            params: { path: { invocation_id: params.id } },
        });
        if (error) {
            rethrowSimpleWithStatus(error, response);
        }
        return data;
    }

    async function fetchInvocationJobsSummary(params: FetchParams): Promise<InvocationJobsSummary> {
        const { data, error, response } = await GalaxyApi().GET("/api/invocations/{invocation_id}/jobs_summary", {
            params: { path: { invocation_id: params.id } },
        });
        if (error) {
            rethrowSimpleWithStatus(error, response);
        }
        return data;
    }

    async function fetchInvocationStepJobsSummary(params: FetchParams): Promise<StepJobSummary[]> {
        const { data, error, response } = await GalaxyApi().GET("/api/invocations/{invocation_id}/step_jobs_summary", {
            params: { path: { invocation_id: params.id } },
        });
        if (error) {
            rethrowSimpleWithStatus(error, response);
        }
        return data;
    }

    async function fetchInvocationMetrics(params: FetchParams): Promise<WorkflowJobMetric[]> {
        const { data, error, response } = await GalaxyApi().GET("/api/invocations/{invocation_id}/metrics", {
            params: { path: { invocation_id: params.id } },
        });
        if (error) {
            rethrowSimpleWithStatus(error, response);
        }
        return data;
    }

    async function fetchInvocationStep(params: FetchParams): Promise<InvocationStep> {
        const { data, error, response } = await GalaxyApi().GET("/api/invocations/steps/{step_id}", {
            params: { path: { step_id: params.id } },
        });
        if (error) {
            rethrowSimpleWithStatus(error, response);
        }
        return data;
    }

    async function fetchInvocationRequest(params: FetchParams): Promise<WorkflowInvocationRequest> {
        const { data, error, response } = await GalaxyApi().GET("/api/invocations/{invocation_id}/request", {
            params: {
                path: {
                    invocation_id: params.id,
                },
            },
        });
        if (error) {
            rethrowSimpleWithStatus(error, response);
        }
        return data;
    }

    async function fetchInvocationCount(params: FetchParams): Promise<number> {
        const { data, error, response } = await GalaxyApi().GET("/api/workflows/{workflow_id}/counts", {
            params: { path: { workflow_id: params.id } },
        });
        if (error) {
            rethrowSimpleWithStatus(error, response);
        }

        let allCounts = 0;
        for (const stateCount of Object.values(data)) {
            if (stateCount) {
                allCounts += stateCount;
            }
        }
        return allCounts;
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
        updateInvocation(invocationId, data);
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

    const { storedItems: storedInvocationMetrics, fetchItemById: fetchInvocationMetricsRawForId } =
        useKeyedCache<WorkflowJobMetric[]>(fetchInvocationMetrics);

    /**
     * For each invocation id, a `step/job id -> number of terminal jobs` mapping as of the last
     * metrics fetch.
     *
     * A *count* (rather than a plain terminal/non-terminal flag) is needed because a single step
     * can have multiple jobs and their metrics (e.g. `runtime_seconds`) wouldn't show up until
     * the entire collection completed.
     *
     * `undefined` means metrics haven't been fetched for this invocation yet.
     */
    const terminalCountsByStepIdAtLastMetricsFetch: Record<string, Record<string, number>> = {};

    function currentTerminalCountsByStepId(invocationId: string): Record<string, number> {
        const stepsJobsSummary = getInvocationStepJobsSummaryById.value(invocationId);
        const counts: Record<string, number> = {};
        for (const step of stepsJobsSummary ?? []) {
            counts[step.id] = numTerminal(step);
        }
        return counts;
    }

    /** Fetches invocation metrics and records the terminal-count mapping for the fetch. */
    async function fetchInvocationMetricsForId(params: FetchParams) {
        // Snapshot *before* fetching, so a job that goes terminal mid-fetch is still seen as new by
        // the next staleness check, rather than being (incorrectly) folded into "already accounted for".
        const snapshotAtFetchStart = currentTerminalCountsByStepId(params.id);
        const result = await fetchInvocationMetricsRawForId(params);
        terminalCountsByStepIdAtLastMetricsFetch[params.id] = snapshotAtFetchStart;
        return result;
    }

    /**
     * Returns the cached metrics for an invocation, fetching once if absent (like `useKeyedCache`'s
     * own accessors) -- but additionally triggers a background refetch (returning the current,
     * possibly-stale cached value immediately, same stale-while-revalidate behavior) whenever any
     * step's terminal-job count has increased since the last fetch (see above for why a count, not a
     * boolean, is needed). This keeps consumers (e.g. the Metrics tab, per-job runtime lookups) fresh
     * as an invocation's jobs finish over time, without every consumer needing its own
     * polling/diffing logic.
     */
    const getInvocationMetricsById = computed(() => {
        return (invocationId: string) => {
            const metrics = storedInvocationMetrics.value[invocationId];
            const oldTerminalCountsByStepId = terminalCountsByStepIdAtLastMetricsFetch[invocationId];

            if (oldTerminalCountsByStepId === undefined) {
                // Never fetched for this invocation -- kick off the initial fetch (via the wrapper,
                // so the terminal-count snapshot gets recorded once it lands).
                fetchInvocationMetricsForId({ id: invocationId });
                return metrics ?? null;
            }

            const newTerminalCountsByStepId = currentTerminalCountsByStepId(invocationId);
            const hasNewlyTerminalJob = Object.entries(newTerminalCountsByStepId).some(
                ([stepId, count]) => count > (oldTerminalCountsByStepId[stepId] ?? 0),
            );
            if (hasNewlyTerminalJob) {
                fetchInvocationMetricsForId({ id: invocationId });
            }
            return metrics ?? null;
        };
    });

    const {
        getItemById: getInvocationStepById,
        fetchItemById: fetchInvocationStepById,
        isLoadingItem: isLoadingInvocationStep,
    } = useKeyedCache<InvocationStep>(fetchInvocationStep);

    const { getItemById: getInvocationRequestById } = useKeyedCache<WorkflowInvocationRequest>(fetchInvocationRequest);

    const { getItemById: getInvocationCountByWorkflowId } = useKeyedCache<number>(fetchInvocationCount);

    const sortedStoredInvocations = computed(() => {
        return Object.values(storedInvocations.value)
            .sort((a, b) => new Date(b.update_time).getTime() - new Date(a.update_time).getTime())
            .filter((invocation) => invocation !== undefined);
    });

    /**
     * A computed function that returns a `job_id -> runtime (wall clock)` lookup for a given
     * invocation, using the `core` plugin's pre-formatted `runtime_seconds` metric value
     * (see `getInvocationMetricsById`).
     */
    const getInvocationJobRuntimeById = computed(() => {
        return (invocationId: string): Record<string, string> => {
            const metrics = getInvocationMetricsById.value(invocationId);
            const runtimeByJobId: Record<string, string> = {};
            for (const metric of metrics ?? []) {
                if (metric.name === "runtime_seconds") {
                    runtimeByJobId[metric.job_id] = metric.value;
                }
            }
            return runtimeByJobId;
        };
    });

    const totalInvocationCount = ref<number | undefined>(undefined);

    return {
        cancelWorkflowScheduling,
        fetchInvocationById,
        fetchInvocationJobsSummaryForId,
        fetchInvocationStepJobsSummaryForId,
        fetchInvocationMetricsForId,
        fetchInvocationStepById,
        getInvocationById,
        getInvocationJobsSummaryById,
        getInvocationStepJobsSummaryById,
        getInvocationMetricsById,
        getInvocationJobRuntimeById,
        getInvocationLoadError,
        getInvocationStepById,
        getInvocationRequestById,
        getInvocationCountByWorkflowId,
        isLoadingInvocation,
        isLoadingInvocationStep,
        sortedStoredInvocations,
        totalInvocationCount,
        updateInvocation,
        /** The current scroll position of the list (used to track where the user has scrolled to). */
        scrollListScrollTop,
    };
});
