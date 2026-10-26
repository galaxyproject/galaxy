<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onUnmounted, ref, watch } from "vue";
import { useRoute } from "vue-router";

import type { RegisteredUser } from "@/api";
import type { JobBaseModel, JobFetchExtraParams, ShowFullJobResponse } from "@/api/jobs";
import { fetchJobs, TERMINAL_STATES } from "@/api/jobs";
import { type JobMatcher, jobsFilterParams, JobsFiltersById, JobsFiltersByName } from "@/components/Jobs/JobsFilters";
import { useResourceWatcher } from "@/composables/resourceWatcher";
import { useJobStore } from "@/stores/jobStore";
import { useToolStore } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";

import GCheckbox from "@/components/BaseComponents/GCheckbox.vue";
import FilterMenu from "@/components/Common/FilterMenu.vue";
import JobCard from "@/components/JobInformation/JobCard.vue";
import JobStatusFilter from "@/components/Jobs/JobStatusFilter.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";
import ScrollList from "@/components/ScrollList/ScrollList.vue";

const HIDDEN_TOOL_IDS = ["__DATA_FETCH__", "upload1"];
const FETCH_LIMIT = 20;

interface Props {
    inPanel?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    inPanel: false,
});

const userStore = useUserStore();
const { currentUser, showToolNamesInJobPanel } = storeToRefs(userStore);

const jobStore = useJobStore();
const { storedJobs } = storeToRefs(jobStore);

const toolStore = useToolStore();

/** Name mode resolves names through the tool store, which nothing else may have loaded yet. */
let toolsRequest: Promise<void> | undefined;
function loadTools() {
    toolsRequest ??= toolStore.fetchTools().catch((error) => {
        toolsRequest = undefined;
        throw error;
    });
    return toolsRequest;
}

const filterText = ref("");
const showAdvanced = ref(false);
const loading = ref(false);

/** Whether upload jobs are fetched */
const includeUploads = ref(false);

/** Total number of jobs matching the current filters. */
const totalJobCount = ref<number | undefined>(undefined);

/** Changing this key remounts the `ScrollList`, so it drops the jobs it has loaded and
 * requests the first page again with the new filters. Name mode changes what the text matches. */
const filterKey = computed(() => {
    const text = filterText.value.trim();
    const filterPart = text ? `${showToolNamesInJobPanel.value ? "name" : "id"}:${text}` : "";
    return `${includeUploads.value}:${filterPart}`;
});

/** The active `status` quick-filter value, or `undefined` if none is toggled on. */
const activeStatusFilter = computed(() => {
    const JobsFilters = showToolNamesInJobPanel.value ? JobsFiltersByName : JobsFiltersById;
    return JobsFilters.getFilterValue(filterText.value, "status") as string | undefined;
});

/**
 * Toggles a `JobStatusFilter` quick-filter button.
 *
 * Setting a `status` filter also clears any manually-picked `state`, since `disablesFilters` can't do
 * this for `status` the other way around (it's not a `FilterMenu` field, so no dropdown-change event
 * exists to trigger it from that side).
 */
function setActiveStatusFilter(group: string | undefined) {
    const JobsFilters = showToolNamesInJobPanel.value ? JobsFiltersByName : JobsFiltersById;
    let newText = JobsFilters.applyFiltersToText({ state: "" }, filterText.value, true);
    newText = group
        ? JobsFilters.applyFiltersToText({ status: group }, newText)
        : JobsFilters.applyFiltersToText({ status: "" }, newText, true);
    filterText.value = newText;
}

/** IDs of jobs fetched for the *current* filters. `storedJobs` is a global, id-keyed
 * cache shared across the whole app, so it can hold jobs from a previous filter. This set
 * scopes the list back down to just what matches the current filters. */
const currentJobIds = ref(new Set<string>());

/** `unretainJob` callbacks from `jobStore.retainJob`, keyed by job id, for jobs added via
 * `addCurrentJob`. */
const unretainJobById = new Map<string, () => void>();

/** Adds `id` to `currentJobIds` and retains it in `jobStore` so it can't be evicted while this
 * panel is showing it. Without this, scrolling past `MAX_CACHED_JOBS` would evict earlier pages'
 * jobs, and the rendered list would stop growing even as new pages load. */
function addCurrentJob(id: string) {
    if (!unretainJobById.has(id)) {
        unretainJobById.set(id, jobStore.retainJob(id));
    }
    currentJobIds.value.add(id);
}

/** Un-retains every job added via `addCurrentJob`, making them evictable again. */
function stopRetainingCurrentJobs() {
    for (const unretainJob of unretainJobById.values()) {
        unretainJob();
    }
    unretainJobById.clear();
}

/** Bumped on every filter change, so pages requested under an earlier filter can be dropped. */
let filterGeneration = 0;

watch(filterKey, () => {
    filterGeneration++;
    stopRetainingCurrentJobs();
    currentJobIds.value = new Set();
    totalJobCount.value = undefined;
    updateTimeMsCache.clear();
});

watch(
    showToolNamesInJobPanel,
    (showToolNames) => {
        if (showToolNames) {
            // Titles fall back to tool ids on failure; `loadJobs` reports errors for name searches.
            loadTools().catch(() => {});
        }
    },
    { immediate: true },
);

/** Matches a job against the current filter text, so a job can be dropped from the list as soon as
 * a live update (e.g. a state change) takes it out of the filter's criteria. Falls back to
 * matching everything if the filter text itself is invalid; `loadJobs` is what reports that error
 * to the user, so this just needs to avoid throwing during render. */
const currentJobMatcher = computed<JobMatcher>(() => {
    if (!filterText.value.trim()) {
        return () => true;
    }
    try {
        return jobsFilterParams(filterText.value, showToolNamesInJobPanel.value).matchesJob;
    } catch {
        return () => true;
    }
});

/** Caches each job's parsed `update_time`, keyed by id, so re-sorting doesn't reparse the date
 * string for a job whose `update_time` hasn't changed since the last sort. Cleared on filter
 * change, alongside the other per-filter state above. */
const updateTimeMsCache = new Map<string, { update_time: string; ms: number }>();

function getUpdateTimeMs(job: ShowFullJobResponse): number {
    const cached = updateTimeMsCache.get(job.id);
    if (cached && cached.update_time === job.update_time) {
        return cached.ms;
    }
    const ms = new Date(job.update_time).getTime();
    updateTimeMsCache.set(job.id, { update_time: job.update_time, ms });
    return ms;
}

/** The sorted jobs matching the current filters, kept up to date reactively as the store updates
 * (e.g. job state changes polled elsewhere), same as `sortedStoredInvocations` for invocations. */
const currentSortedJobs = computed(() => {
    return [...currentJobIds.value]
        .map((id) => storedJobs.value[id])
        .filter((job): job is ShowFullJobResponse => job !== undefined && currentJobMatcher.value(job))
        .sort((a, b) => getUpdateTimeMs(b) - getUpdateTimeMs(a));
});

/** For non-terminal (and non-paused) jobs that are currently displayed, so they can be polled for updates. */
const pollableJobIds = computed(() =>
    currentSortedJobs.value
        .filter((job) => !TERMINAL_STATES.includes(job.state) && job.state !== "paused")
        .map((job) => job.id),
);

/** Refreshes every currently-pollable job in one request. */
async function pollActiveJobs() {
    const ids = pollableJobIds.value;
    if (ids.length === 0) {
        return;
    }
    const [jobs] = await fetchJobs(0, ids.length, { job_id: ids });
    for (const job of jobs) {
        jobStore.updateJob(job.id, job);
    }
}

const activeJobsWatcher = useResourceWatcher(pollActiveJobs);

/**
 * Used to trigger the watcher whenever the set of pollable job IDs changes, ensuring non-terminal
 * (and non-paused) jobs are polled immediately.
 */
const pollableJobIdsKey = computed(() => [...pollableJobIds.value].sort().join(","));

// Restarting on every change picks up newly displayed jobs immediately, instead of waiting for
// the next scheduled tick.
watch(pollableJobIdsKey, () => activeJobsWatcher.startWatchingResource(), { immediate: true });

/** If user information is available, determines whether the job belongs to another user. */
function belongsToAnotherUser(job: ShowFullJobResponse): boolean {
    if (job.user_id !== undefined && job.user_id !== null) {
        return !userStore.matchesCurrentUserId(job.user_id);
    }
    if (job.user_email) {
        return job.user_email !== (currentUser.value as RegisteredUser | null)?.email;
    }
    return false;
}

/** The IDs of all jobs currently stored in the job store. */
const storedJobIds = computed(() => Object.keys(storedJobs.value));

// Ensure any jobs added to the store while no filter is active are included in `currentJobIds`
// (these would be jobs not already included in the paginated set; think a job submitted while the panel is open)
watch(storedJobIds, (ids) => {
    if (filterText.value.trim()) {
        return;
    }
    for (const id of ids) {
        const job = storedJobs.value[id];
        if (job && (includeUploads.value || !HIDDEN_TOOL_IDS.includes(job.tool_id)) && !belongsToAnotherUser(job)) {
            addCurrentJob(id);
        }
    }
});

function buildFetchExtraProps(userId: string, includeTotalCount: boolean): JobFetchExtraParams {
    return {
        user_id: userId,
        exclude_tool_ids: includeUploads.value ? undefined : HIDDEN_TOOL_IDS,
        ...jobsFilterParams(filterText.value, showToolNamesInJobPanel.value).params,
        include_total_count: includeTotalCount,
    };
}

/** Flag indicating whether this is the first check for new matching jobs. */
let isFirstCheck = true;

/**
 * Periodically rechecks the first page so a job that starts matching the current filter, or a
 * brand new job no other view has touched, is found even though it was never fetched into
 * `currentJobIds`.
 */
async function checkForNewMatchingJobs() {
    if (isFirstCheck) {
        isFirstCheck = false;
        return;
    }
    if (!currentUser.value || currentUser.value.isAnonymous) {
        return;
    }
    const extraProps = buildFetchExtraProps(currentUser.value.id, false);
    const [data] = await fetchJobs(0, FETCH_LIMIT, extraProps, "create_time");
    for (const item of data) {
        addCurrentJob(item.id);
        jobStore.updateJob(item.id, item);
    }
}

const newJobsWatcher = useResourceWatcher(checkForNewMatchingJobs);
newJobsWatcher.startWatchingResource();

onUnmounted(() => {
    stopRetainingCurrentJobs();
    activeJobsWatcher.dispose();
    newJobsWatcher.dispose();
});

async function loadJobs(offset: number, limit: number) {
    if (!currentUser.value || currentUser.value.isAnonymous) {
        return { items: [], total: 0 };
    }
    const requestGeneration = filterGeneration;
    const userId = currentUser.value.id;

    // Set before anything that can throw (loadTools, buildFetchExtraProps), so a failure here
    // still goes through the same generation-aware clearing below instead of leaving a stale
    // in-flight request from an earlier generation as the only thing that could have cleared it.
    loading.value = true;
    let data: JobBaseModel[];
    let totalMatches: number;
    try {
        if (showToolNamesInJobPanel.value) {
            await loadTools();
        }
        // Only the first page needs the count; it doesn't change page to page under the same filters.
        const extraProps = buildFetchExtraProps(userId, offset === 0);
        [data, totalMatches] = await fetchJobs(offset, limit, extraProps, "create_time");
    } finally {
        // A discarded page's own cleanup must not clear the spinner out from under a newer,
        // still-in-flight request for the current filter.
        if (requestGeneration === filterGeneration) {
            loading.value = false;
        }
    }
    if (requestGeneration !== filterGeneration) {
        // Filters changed while loading; this page belongs to the discarded list.
        return { items: [], total: 0 };
    }

    for (const item of data) {
        addCurrentJob(item.id);
        jobStore.updateJob(item.id, item);
    }

    if (offset === 0) {
        totalJobCount.value = totalMatches;
    }
    return { items: currentSortedJobs.value, total: totalJobCount.value ?? 0 };
}

const route = useRoute();

const currentItemId = computed(() => {
    const match = route.path.match(/\/jobs\/([a-zA-Z0-9]+)\/view/);
    return match ? match[1] : undefined;
});
</script>

<template>
    <ActivityPanel title="Jobs">
        <template v-slot:header-buttons>
            <div class="job-panel-header-toggles">
                <GCheckbox
                    v-model="showToolNamesInJobPanel"
                    v-g-tooltip.hover
                    data-test-id="job-panel-name-mode-toggle"
                    size="small"
                    switch
                    title="Show/Search tool names instead of IDs">
                    <span class="text-nowrap small unselectable">Tool Names</span>
                </GCheckbox>
                <GCheckbox
                    v-model="includeUploads"
                    v-g-tooltip.hover
                    data-test-id="job-panel-include-uploads-toggle"
                    size="small"
                    switch
                    title="Include upload jobs in this list">
                    <span class="small unselectable">Uploads</span>
                </GCheckbox>
            </div>
        </template>

        <template v-slot:header>
            <FilterMenu
                v-model:filter-text="filterText"
                v-model:show-advanced="showAdvanced"
                name="Jobs"
                :placeholder="`search jobs by tool ${showToolNamesInJobPanel ? 'name' : 'ID'}`"
                :filter-class="showToolNamesInJobPanel ? JobsFiltersByName : JobsFiltersById"
                :loading="loading" />

            <JobStatusFilter
                v-if="!showAdvanced"
                class="pt-2"
                :active-group="activeStatusFilter"
                @update:active-group="setActiveStatusFilter" />
        </template>

        <ScrollList
            v-show="!showAdvanced"
            :key="filterKey"
            :loader="loadJobs"
            :limit="FETCH_LIMIT"
            :item-key="(job) => job.id"
            :in-panel="props.inPanel"
            :prop-items="currentSortedJobs"
            :prop-total-count="totalJobCount"
            adjust-for-total-count-changes
            retry-message="Clear your search or click the button at the bottom of the list to retry."
            name="job"
            name-plural="jobs"
            :load-disabled="!currentUser || currentUser.isAnonymous">
            <template v-slot:item="{ item: job }">
                <JobCard :job="job" :current="job.id === currentItemId" :show-tool-name="showToolNamesInJobPanel" />
            </template>
        </ScrollList>
    </ActivityPanel>
</template>

<style scoped lang="scss">
.job-panel-header-toggles {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.25rem 0.5rem;
    justify-content: flex-end;
}
</style>
