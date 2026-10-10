import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { GalaxyApi } from "@/api";
import { type ResponseVal, type ShowFullJobResponse, TERMINAL_STATES } from "@/api/jobs";
import { useResourceWatcher } from "@/composables/resourceWatcher";
import { isRetryableApiError, MAX_RETRIES, rethrowSimpleWithStatus } from "@/utils/simple-error";

interface JobFetchParams {
    id: string;
    /** Whether to request the full job representation. Defaults to `true`. */
    full?: boolean;
}

interface PollEntry {
    watcher: ReturnType<typeof useResourceWatcher>;
    full: boolean;
    refCount: number;
}

/** Cache target; mounted consumers and in-flight requests may temporarily exceed it. */
export const MAX_CACHED_JOBS = 40;

/**
 * The Job store for managing job data and tool-run responses.
 *
 * - Keeps recently used jobs, evicting unused entries above `MAX_CACHED_JOBS`.
 *   Mounted consumers retain their entries even after polling finishes.
 * - Allows both base and full requests for the same job id to be tracked independently, but merges
 *   the full response into the cached job rather than overwriting it entirely.
 * - Polls a job until it reaches a terminal state, deduped so multiple callers watching the same
 *   job share one poll.
 * - Stores the latest tool-run response (used by the post-run "success" view).
 */
export const useJobStore = defineStore("jobStore", () => {
    const latestResponse = ref<ResponseVal | null>(null);

    const storedJobs = ref<{ [id: string]: ShowFullJobResponse }>({});
    const loadingErrors = ref<{ [id: string]: Error }>({});
    const retryCounts: { [id: string]: number } = {};

    /** Keyed by `id:full` so a base and a full request for the same job id are tracked separately.
     * Otherwise whichever one resolved first would be (wrongly) treated as satisfying both.
     */
    const loadingRequests = new Map<string, Promise<ShowFullJobResponse | undefined>>();

    /** Counts in-flight requests per job id (a base and a full request can be in flight for the
     * same id at once, under separate `loadingRequests` keys) so `isLoadingJob` stays true until
     * *all* of them finish, not just whichever happens to resolve first. */
    const loadingCountsByJobId = ref<{ [id: string]: number }>({});

    function saveLatestResponse(newResponse: ResponseVal) {
        latestResponse.value = newResponse;
    }

    /** Keys a request by `id:full` so that base and full **requests** for the same job id are tracked separately. */
    function requestKey(params: JobFetchParams): string {
        return `${params.id}:${params.full ?? true}`;
    }

    /** Whether a failed fetch for `id` is worth retrying: the error is a retryable status and we
     * haven't already retried it `MAX_RETRIES` times. */
    function canRetryJob(id: string): boolean {
        const existingError = loadingErrors.value[id];
        return !!existingError && isRetryableApiError(existingError) && (retryCounts[id] ?? 0) <= MAX_RETRIES;
    }

    const getJobLoadError = computed(() => (id: string) => loadingErrors.value[id] ?? null);

    const isLoadingJob = computed(() => (id: string) => (loadingCountsByJobId.value[id] ?? 0) > 0);

    function mergeJob(freshJob: ShowFullJobResponse, existingJob?: ShowFullJobResponse): ShowFullJobResponse {
        return existingJob ? { ...existingJob, ...freshJob } : freshJob;
    }

    async function fetchJobFromApi(params: JobFetchParams): Promise<ShowFullJobResponse> {
        const { data, error, response } = await GalaxyApi().GET("/api/jobs/{job_id}", {
            params: { path: { job_id: params.id }, query: { full: params.full ?? true } },
        });
        if (error) {
            rethrowSimpleWithStatus(error, response);
        }
        return data;
    }

    /** Fetches a job, deduping concurrent requests for the same id+`full` shape, merging the
     * result into the cache, and tracking loading/retry state. */
    async function fetchAndCacheJob(params: JobFetchParams): Promise<ShowFullJobResponse | undefined> {
        const key = requestKey(params);
        const inFlight = loadingRequests.get(key);
        if (inFlight) {
            return inFlight;
        }

        // Increment the count of in-flight requests for this job id. This ensures that `isLoadingJob`
        // remains true until all concurrent requests for the same job id (base and full) have completed.
        loadingCountsByJobId.value[params.id] = (loadingCountsByJobId.value[params.id] ?? 0) + 1;

        const fetchPromise = (async () => {
            try {
                const freshJob = await fetchJobFromApi(params);
                const existingJob = storedJobs.value[params.id];
                const job = mergeJob(freshJob, existingJob);
                storedJobs.value[params.id] = job;
                delete loadingErrors.value[params.id];
                delete retryCounts[params.id];
                if (params.full !== false && TERMINAL_STATES.includes(freshJob.state)) {
                    terminalFullJobIds.add(params.id);
                } else if (params.full !== false || freshJob.state !== existingJob?.state) {
                    terminalFullJobIds.delete(params.id);
                }
                return job;
            } catch (error) {
                retryCounts[params.id] = (retryCounts[params.id] ?? 0) + 1;
                loadingErrors.value[params.id] = error as Error;
                return undefined;
            } finally {
                loadingRequests.delete(key);
                const remaining = (loadingCountsByJobId.value[params.id] ?? 1) - 1;
                if (remaining <= 0) {
                    delete loadingCountsByJobId.value[params.id];
                } else {
                    loadingCountsByJobId.value[params.id] = remaining;
                }
            }
        })();

        loadingRequests.set(key, fetchPromise);
        return fetchPromise;
    }

    function removeJob(id: string) {
        delete storedJobs.value[id];
        delete loadingErrors.value[id];
        delete retryCounts[id];
    }

    // LRU tracking for `MAX_CACHED_JOBS`: a Map's keys iterate oldest-to-newest, and re-`set`ting
    // a key moves it to the end, so this alone tracks recency order without extra bookkeeping.
    const lruOrder = new Map<string, true>();

    function markUsed(id: string) {
        lruOrder.delete(id);
        lruOrder.set(id, true);
    }

    const consumers = new Map<string, number>();

    /** Protects a displayed job from eviction until the returned release function is called. */
    function retainJob(id: string) {
        consumers.set(id, (consumers.get(id) ?? 0) + 1);
        let released = false;
        return () => {
            if (released) {
                return;
            }
            released = true;
            const remaining = (consumers.get(id) ?? 1) - 1;
            if (remaining > 0) {
                consumers.set(id, remaining);
            } else {
                consumers.delete(id);
            }
            evictIfOverCap();
        };
    }

    function evictIfOverCap() {
        for (const id of lruOrder.keys()) {
            if (lruOrder.size <= MAX_CACHED_JOBS) {
                break;
            }
            if (consumers.has(id) || activePolls.has(id) || isLoadingJob.value(id)) {
                continue;
            }
            lruOrder.delete(id);
            removeJob(id);
            terminalFullJobIds.delete(id);
        }
    }

    /** An overloaded fetch function that ensures the job is retrieved from the cache, but with the
     * additional, optional `full` option for requesting the full job representation. */
    async function fetchJob(params: JobFetchParams) {
        markUsed(params.id);
        const job = await fetchAndCacheJob(params);
        evictIfOverCap();
        return job;
    }

    /** Reads the cache without starting a request. */
    const getCachedJob = computed(() => (id: string) => {
        const job = storedJobs.value[id] ?? null;
        if (job) {
            markUsed(id);
        }
        return job;
    });

    /** One-off lookup. Mounted readers use `useJobDetails` to retain their cache entries. */
    const getJob = computed(() => (id: string) => {
        const job = getCachedJob.value(id);
        if (!job && id && !loadingRequests.has(requestKey({ id })) && !getJobLoadError.value(id)) {
            fetchJob({ id });
        }
        return job;
    });

    // Full-only fields are final only when a full response itself observed completion.
    const terminalFullJobIds = new Set<string>();

    /** A track of all active polls (by `job_id` and whether the stored representation is full),
     * plus a count of how many callers still want that poll running, so we don't duplicate polls
     * for the same ID and stop polling once the last interested caller goes away. */
    const activePolls = new Map<string, PollEntry>();

    /**
     * Polls a job until it reaches a terminal state. If the job is already terminal and cached,
     * it may not poll at all. If the stored job is not a full representation and a full one is
     * requested, it will poll for the final full representation, including retries on transient errors.
     *
     * Returns a `stopWatchingJob` function the caller must invoke (e.g. from `onUnmounted`) once it
     * no longer needs this job polled because the underlying poll only actually stops once every caller
     * that started it has done so.
     */
    function pollJobUntilTerminal(params: JobFetchParams): { stopWatchingJob: () => void } {
        const { id, full = true } = params;
        const stopWatchingReturn = { stopWatchingJob: () => {} };

        // Not using `getJob` here because that would trigger a fetch if the job isn't already cached
        const cachedJob = storedJobs.value[id];
        const cachedJobIsTerminal = !!cachedJob && TERMINAL_STATES.indexOf(cachedJob.state) !== -1;

        /** Whether the cached job satisfies the current request, considering the `full` option. */
        const cacheSatisfiesRequest = full ? terminalFullJobIds.has(id) : !!cachedJob;
        if (cachedJobIsTerminal && cacheSatisfiesRequest) {
            // Already have everything this call needs, and the job won't change anymore.
            return stopWatchingReturn;
        }

        const runningPoll = activePolls.get(id);
        if (runningPoll !== undefined) {
            runningPoll.refCount++;
            // We need to switch an ongoing non-`full` poll to request `full`.
            if (full && !runningPoll.full) {
                runningPoll.full = true;
            }
            return { stopWatchingJob: () => stopWatchingJob(id, runningPoll) };
        }

        const watcher = useResourceWatcher(
            async () => {
                // Read (not close over) the current requested level as a later call may have
                // upgraded this poll to `full: true` since it started.
                const requestFull = activePolls.get(id)?.full ?? full;
                let job = await fetchJob({ id, full: requestFull });
                if (activePolls.get(id) !== pollEntry) {
                    return;
                }
                if (job && TERMINAL_STATES.indexOf(job.state) !== -1) {
                    // An in-flight base request may finish after a full consumer joins.
                    // Fetch final full fields before stopping the shared poll.
                    if (activePolls.get(id)?.full && !terminalFullJobIds.has(id)) {
                        job = await fetchJob({ id, full: true });
                    }
                    if (job && TERMINAL_STATES.includes(job.state)) {
                        watcher.dispose();
                        if (activePolls.get(id) === pollEntry) {
                            activePolls.delete(id);
                        }
                        return;
                    }
                }
                if (!job && getJobLoadError.value(id) && !canRetryJob(id)) {
                    // Stop fetching if the fetch failed with a non-retryable error
                    watcher.dispose();
                    activePolls.delete(id);
                }
            },
            { shortPollingInterval: 1000, longPollingInterval: 1000 },
        );
        const pollEntry = { watcher, full, refCount: 1 };
        activePolls.set(id, pollEntry);
        watcher.startWatchingResource();
        return { stopWatchingJob: () => stopWatchingJob(id, pollEntry) };
    }

    /** One caller is done watching a job; the poll stops once refCount hits 0.
     *
     * `entry` is the specific poll entry this caller's handle was issued for.
     * If `id`'s current entry in `activePolls` is a *different* one (the original poll already ended
     * and a new one started for the same id since), this is a stale handle and must be a no-op:
     * decrementing the new, unrelated poll's `refCount` could stop it while a still-active caller
     * still needs it.
     */
    function stopWatchingJob(id: string, entry: PollEntry) {
        const runningPoll = activePolls.get(id);
        if (!runningPoll || runningPoll !== entry) {
            return;
        }
        runningPoll.refCount--;
        if (runningPoll.refCount <= 0) {
            runningPoll.watcher.dispose();
            activePolls.delete(id);
        }
    }

    return {
        fetchJob,
        saveLatestResponse,
        getJob,
        getCachedJob,
        retainJob,
        getJobLoadError,
        isLoadingJob,
        latestResponse,
        pollJobUntilTerminal,
    };
});
