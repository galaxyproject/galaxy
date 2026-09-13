import { defineStore } from "pinia";
import { computed, ref, set } from "vue";

import { GalaxyApi } from "@/api";
import {
    type InvocationJobsSummary,
    type InvocationStep,
    isWorkflowInvocationElementView,
    type StepJobSummary,
    type WorkflowInvocation,
    type WorkflowInvocationRequest,
    type WorkflowJobMetric,
} from "@/api/invocations";
import { getData as getInvocationsData } from "@/components/Grid/configs/invocations";
import { numTerminal } from "@/components/WorkflowInvocationState/util";
import { type FetchParams, useKeyedCache } from "@/composables/keyedCache";
import { useHistoryStore } from "@/stores/historyStore";
import { useWorkflowStore } from "@/stores/workflowStore";
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

    /**
     * `fetchLatestInvocations` seeds this cache with list summaries: the invocations index serializes the
     * collection view, which has no `steps`, `inputs` or `outputs`. So `getInvocationById` must upgrade a
     * cached summary to the element view rather than treat it as already loaded.
     */
    const shouldFetchInvocationDetails = computed(() => {
        return (invocation?: WorkflowInvocation) => !invocation || !isWorkflowInvocationElementView(invocation);
    });

    const {
        fetchItemById: fetchInvocationById,
        getItemById: getInvocationById,
        getItemLoadError: getInvocationLoadError,
        isLoadingItem: isLoadingInvocation,
        storedItems: storedInvocations,
    } = useKeyedCache<WorkflowInvocation>(fetchInvocationDetails, shouldFetchInvocationDetails);

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

    /**
     * Returns `null` if the step jobs summary hasn't loaded yet (it's fetched/kept fresh
     * independently, e.g. by `WorkflowInvocationState.vue`'s polling) -- callers must treat that as
     * "unknown" rather than "zero terminal jobs", otherwise the summary arriving a moment later would
     * look like a burst of newly-terminal jobs and trigger a spurious extra fetch.
     */
    function currentTerminalCountsByStepId(invocationId: string): Record<string, number> | null {
        const stepsJobsSummary = getInvocationStepJobsSummaryById.value(invocationId);
        if (!stepsJobsSummary) {
            return null;
        }
        const counts: Record<string, number> = {};
        for (const step of stepsJobsSummary) {
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
        // The step jobs summary may not have loaded yet when this fetch started (snapshot `null`) --
        // fall back to whatever it looks like now, so we don't leave the snapshot permanently
        // unrecorded (which would make every future read think metrics were "never fetched").
        const snapshot = snapshotAtFetchStart ?? currentTerminalCountsByStepId(params.id);
        if (snapshot !== null) {
            terminalCountsByStepIdAtLastMetricsFetch[params.id] = snapshot;
        }
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
            // Step jobs summary not loaded (yet, or anymore) -- nothing to compare against, so don't
            // fetch based on incomplete information.
            const hasNewlyTerminalJob =
                newTerminalCountsByStepId !== null &&
                Object.entries(newTerminalCountsByStepId).some(
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

    const { getItemById: getInvocationRequestById, getItemLoadError: getInvocationRequestByIdError } =
        useKeyedCache<WorkflowInvocationRequest>(fetchInvocationRequest);

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

    /** Ids of the most recently created invocations, in the order the server returned them. */
    const latestInvocationIds = ref<string[]>([]);
    const isLoadingLatestInvocations = ref(false);
    /**
     * Whether the latest invocations have been fetched at least once. An empty
     * result counts as loaded, so consumers can tell "nothing invoked yet" from
     * "not fetched yet" instead of requesting the list over and over.
     */
    const hasLoadedLatestInvocations = ref(false);
    let latestInvocationsPromise: Promise<WorkflowInvocation[]> | null = null;

    /**
     * The latest invocation summaries (see `fetchLatestInvocations`), resolved against the shared
     * invocation cache -- so consumers always see the freshest version of an invocation, no matter
     * which part of the app loaded it.
     */
    const latestInvocations = computed<WorkflowInvocation[]>(() =>
        latestInvocationIds.value
            .map((id) => storedInvocations.value[id])
            .filter((invocation): invocation is WorkflowInvocation => invocation !== undefined),
    );

    /**
     * Resolves the history and workflow names an invocation is displayed with.
     *
     * The grid's `getData` starts these lookups but does not await them, so a
     * list rendered right after the fetch (the command palette) would show bare
     * ids. Both stores share their in-flight request per id, so awaiting the
     * same lookups here adds no requests. A failing lookup only costs a name,
     * never the invocation row, and is therefore ignored.
     */
    async function fetchInvocationNames(invocations: WorkflowInvocation[]) {
        const historyStore = useHistoryStore();
        const workflowStore = useWorkflowStore();
        const historyIds = new Set(invocations.map((invocation) => invocation.history_id).filter(Boolean));
        const workflowIds = new Set(invocations.map((invocation) => invocation.workflow_id).filter(Boolean));
        await Promise.all([
            ...[...historyIds].map((historyId) =>
                historyStore.getHistoryById(historyId, false)
                    ? Promise.resolve()
                    : historyStore.loadHistoryById(historyId).catch(() => undefined),
            ),
            ...[...workflowIds].map((workflowId) =>
                workflowStore.fetchWorkflowForInstanceIdCached(workflowId).catch(() => undefined),
            ),
        ]);
    }

    /**
     * Fetches the `limit` most recently created invocations and merges them into the shared
     * invocation cache (no separate copy of the data is kept -- only the ordered list of ids).
     *
     * Reuses the invocations grid's `getData`, which also populates the history and workflow name
     * caches needed to display an invocation. Concurrent calls share a single request.
     */
    async function fetchLatestInvocations(limit = 15): Promise<WorkflowInvocation[]> {
        if (latestInvocationsPromise) {
            return latestInvocationsPromise;
        }
        isLoadingLatestInvocations.value = true;
        latestInvocationsPromise = (async () => {
            try {
                const [invocations] = await getInvocationsData(0, limit, "", "create_time", true);
                const ids: string[] = [];
                for (const invocation of invocations) {
                    updateInvocation(invocation.id, invocation);
                    if (!ids.includes(invocation.id)) {
                        ids.push(invocation.id);
                    }
                }
                latestInvocationIds.value = ids;
                hasLoadedLatestInvocations.value = true;
                await fetchInvocationNames(invocations);
                return latestInvocations.value;
            } finally {
                isLoadingLatestInvocations.value = false;
                latestInvocationsPromise = null;
            }
        })();
        return latestInvocationsPromise;
    }

    return {
        cancelWorkflowScheduling,
        fetchLatestInvocations,
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
        getInvocationRequestByIdError,
        getInvocationCountByWorkflowId,
        hasLoadedLatestInvocations,
        isLoadingInvocation,
        isLoadingInvocationStep,
        isLoadingLatestInvocations,
        latestInvocations,
        sortedStoredInvocations,
        totalInvocationCount,
        updateInvocation,
        /** The current scroll position of the list (used to track where the user has scrolled to). */
        scrollListScrollTop,
    };
});
