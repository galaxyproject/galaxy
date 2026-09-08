import { defineStore } from "pinia";
import { computed, ref, set } from "vue";

import { GalaxyApi } from "@/api";
import type { StoredWorkflowDetailed, WorkflowSortBy, WorkflowSummary } from "@/api/workflows";
import { loadWorkflows } from "@/api/workflows";
import { getWorkflowFull } from "@/components/Workflow/workflows.services";

/** The workflow lists the store keeps ordered id caches for. */
export type WorkflowListVariant = "my" | "shared" | "published" | "bookmarked";

export interface FetchWorkflowListOptions {
    sortBy?: WorkflowSortBy;
    sortDesc?: boolean;
    limit?: number;
    offset?: number;
}

type NormalizedFetchWorkflowListOptions = Required<FetchWorkflowListOptions>;

function normalizeListOptions(options: FetchWorkflowListOptions = {}): NormalizedFetchWorkflowListOptions {
    const { sortBy = "update_time", sortDesc = true, limit = 20, offset = 0 } = options;
    return { sortBy, sortDesc, limit, offset };
}

/**
 * Filter token and query params each variant adds on top of the user provided query.
 *
 * `showShared` is always spelled out: the backend defaults `show_shared` to true
 * and an `undefined` value is dropped from the query string altogether, so the
 * lists of the user's own workflows have to ask for `false` explicitly to stay
 * free of workflows that were only shared with them.
 */
function variantParams(variant: WorkflowListVariant, query: string) {
    const filters = query.trim() ? [query.trim()] : [];

    switch (variant) {
        case "shared":
            filters.push("is:shared_with_me");
            return { filterText: filters.join(" "), showPublished: false, showShared: true };
        case "published":
            filters.push("is:published");
            return { filterText: filters.join(" "), showPublished: true, showShared: undefined };
        case "bookmarked":
            filters.push("is:bookmarked");
            return { filterText: filters.join(" "), showPublished: false, showShared: false };
        default:
            return { filterText: filters.join(" "), showPublished: false, showShared: false };
    }
}

export const useWorkflowStore = defineStore("workflowStore", () => {
    const workflowsByInstanceId = ref<{ [index: string]: StoredWorkflowDetailed }>({});
    const fullWorkflowsByIdAndVersion = ref(new Map<string, any>());

    /** Single cache of workflow summaries, keyed by workflow id. */
    const workflowSummariesById = ref<{ [index: string]: WorkflowSummary }>({});

    /** Ordered workflow ids per normalized request -- ids only, never copies of the summaries. */
    const listIdsByKey = ref<{ [index: string]: string[] }>({});

    /** In progress list fetches, to avoid firing the same request twice. */
    const listPromises = new Map<string, Promise<WorkflowSummary[]>>();

    function listKey(variant: WorkflowListVariant, query = "", options: FetchWorkflowListOptions = {}) {
        const { sortBy, sortDesc, limit, offset } = normalizeListOptions(options);
        return JSON.stringify([variant, query.trim(), sortBy, sortDesc, limit, offset]);
    }

    const getWorkflowSummaryById = computed(() => (workflowId: string) => workflowSummariesById.value[workflowId]);

    const allWorkflowSummaries = computed(() => Object.values(workflowSummariesById.value));

    /** Summaries for a cached list, in the order the backend returned them. */
    const getWorkflowList = computed(
        () =>
            (variant: WorkflowListVariant, query = "", options: FetchWorkflowListOptions = {}) => {
                const ids = listIdsByKey.value[listKey(variant, query, options)] ?? [];
                return ids
                    .map((workflowId) => workflowSummariesById.value[workflowId])
                    .filter((workflow): workflow is WorkflowSummary => Boolean(workflow));
            },
    );

    /** Whether a list has been fetched at least once (an empty result still counts as loaded). */
    const isWorkflowListLoaded = computed(
        () =>
            (variant: WorkflowListVariant, query = "", options: FetchWorkflowListOptions = {}) =>
                listKey(variant, query, options) in listIdsByKey.value,
    );

    /** Merges summaries into the cache, updating existing entries instead of duplicating them. */
    function mergeWorkflowSummaries(workflows: WorkflowSummary[]) {
        workflows.forEach((workflow) => {
            const cached = workflowSummariesById.value[workflow.id];
            set(workflowSummariesById.value, workflow.id, cached ? { ...cached, ...workflow } : workflow);
        });
    }

    async function fetchAndMergeWorkflowList(
        key: string,
        variant: WorkflowListVariant,
        query: string,
        options: NormalizedFetchWorkflowListOptions,
    ) {
        const { sortBy, sortDesc, limit, offset } = options;
        const { filterText, showPublished, showShared } = variantParams(variant, query);

        try {
            const { data } = await loadWorkflows({
                sortBy,
                sortDesc,
                limit,
                offset,
                filterText,
                showPublished,
                showShared,
                skipStepCounts: true,
            });

            mergeWorkflowSummaries(data);
            set(
                listIdsByKey.value,
                key,
                data.map((workflow) => workflow.id),
            );

            return getWorkflowList.value(variant, query, options);
        } finally {
            listPromises.delete(key);
        }
    }

    /**
     * Fetches a workflow list and merges it into the summary cache.
     * @param variant which list to fetch
     * @param query optional free text search
     * @param options sorting and paging overrides
     */
    function fetchWorkflowList(
        variant: WorkflowListVariant,
        query = "",
        options: FetchWorkflowListOptions = {},
    ): Promise<WorkflowSummary[]> {
        const normalizedOptions = normalizeListOptions(options);
        const key = listKey(variant, query, normalizedOptions);

        const existingPromise = listPromises.get(key);
        if (existingPromise) {
            return existingPromise;
        }

        const promise = fetchAndMergeWorkflowList(key, variant, query, normalizedOptions);
        listPromises.set(key, promise);
        return promise;
    }

    /** Cached promises for fetching full workflows to prevent duplicate requests */
    const fullWorkflowPromises = new Map<string, Promise<any>>();

    const getStoredWorkflowByInstanceId = computed(() => (workflowId: string) => {
        return workflowsByInstanceId.value[workflowId];
    });

    const getStoredWorkflowIdByInstanceId = computed(() => (workflowId: string) => {
        const storedWorkflow = workflowsByInstanceId.value[workflowId];
        return storedWorkflow?.id;
    });

    const getStoredWorkflowNameByInstanceId = computed(() => (workflowId: string, defaultName = "...") => {
        const details = workflowsByInstanceId.value[workflowId];
        if (details && details.name) {
            return details.name;
        } else {
            return defaultName;
        }
    });

    // TODO: A better way? Could use ref<{ [id: string]: { [version: string]: any } }>({});
    function uniqueIdAndVersionKey(workflowId: string, version?: number) {
        return `${workflowId}${version ? `_${version}` : "_latest"}`;
    }

    /**
     * Fetches full workflow details, avoiding multiple fetches occurring simultaneously.
     * If a fetch is already in progress for the same workflow+version, subsequent callers
     * will await the same promise instead of initiating a new request.
     * @param workflowId workflow id
     * @param version optional version number
     */
    async function getFullWorkflowCached(workflowId: string, version?: number) {
        const key = uniqueIdAndVersionKey(workflowId, version);

        // Return cached workflow if already fetched
        if (fullWorkflowsByIdAndVersion.value.has(key)) {
            return fullWorkflowsByIdAndVersion.value.get(key);
        }

        // Check if a fetch is already in progress for this workflow+version
        const existingPromise = fullWorkflowPromises.get(key);
        if (existingPromise) {
            await existingPromise;
            // After the promise resolves, the workflow should be in cache
            return fullWorkflowsByIdAndVersion.value.get(key);
        }

        // Fetch the full workflow and store the promise
        const fetchPromise = getWorkflowFull(workflowId, version);
        fullWorkflowPromises.set(key, fetchPromise);

        try {
            const storedWorkflow = await fetchPromise;
            if (storedWorkflow) {
                fullWorkflowsByIdAndVersion.value.set(key, storedWorkflow);
            }
            return storedWorkflow;
        } finally {
            // Remove promise from tracking map
            fullWorkflowPromises.delete(key);
        }
    }

    // stores in progress promises to avoid overlapping requests
    const workflowDetailPromises = new Map<string, Promise<unknown>>();

    /**
     * Fetches workflow details, avoiding multiple fetches occurring simultaneously
     * @param workflowId instance id of workflow to fetch
     */
    async function fetchWorkflowForInstanceId(workflowId: string) {
        const promise = workflowDetailPromises.get(workflowId);
        if (promise) {
            console.debug("Workflow details fetching already requested for", workflowId);
            await promise;
        } else {
            console.debug("Fetching workflow details for", workflowId);
            const promise = GalaxyApi().GET("/api/workflows/{workflow_id}", {
                params: {
                    path: { workflow_id: workflowId },
                    query: { instance: true },
                },
            });
            workflowDetailPromises.set(workflowId, promise);
            const { data, error } = await promise;
            if (error) {
                throw Error(`Failed to retrieve workflow. ${error.err_msg}`);
            }
            set(workflowsByInstanceId.value, workflowId, data);
        }
        workflowDetailPromises.delete(workflowId);
    }

    /**
     * Fetches workflow details only if they are not already in the store
     * @param workflowId instance id of workflow to maybe fetch
     */
    async function fetchWorkflowForInstanceIdCached(workflowId: string) {
        if (!Object.keys(workflowsByInstanceId.value).includes(workflowId)) {
            await fetchWorkflowForInstanceId(workflowId);
        }
    }

    return {
        allWorkflowSummaries,
        fetchWorkflowForInstanceId,
        fetchWorkflowForInstanceIdCached,
        fetchWorkflowList,
        getFullWorkflowCached,
        getStoredWorkflowByInstanceId,
        getStoredWorkflowIdByInstanceId,
        getStoredWorkflowNameByInstanceId,
        getWorkflowList,
        getWorkflowSummaryById,
        isWorkflowListLoaded,
        workflowsByInstanceId,
        workflowSummariesById,
    };
});
