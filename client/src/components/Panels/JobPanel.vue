<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onUnmounted, ref, watch } from "vue";
import { useRoute } from "vue-router";

import type { RegisteredUser } from "@/api";
import type { JobBaseModel, JobFetchExtraParams, ShowFullJobResponse } from "@/api/jobs";
import { fetchJobs } from "@/api/jobs";
import { jobsFilterParams, JobsFiltersById, JobsFiltersByName } from "@/components/Jobs/JobsFilters";
import { useJobStore } from "@/stores/jobStore";
import { useToolStore } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";

import GCheckbox from "@/components/BaseComponents/GCheckbox.vue";
import FilterMenu from "@/components/Common/FilterMenu.vue";
import JobCard from "@/components/JobInformation/JobCard.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";
import ScrollList from "@/components/ScrollList/ScrollList.vue";

const HIDDEN_TOOL_IDS = ["__DATA_FETCH__", "upload1"];

interface Props {
    inPanel?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    inPanel: false,
});

const userStore = useUserStore();
const { currentUser, showToolNamesInJobPanel } = storeToRefs(userStore);

const jobStore = useJobStore();
const { sortedStoredJobs } = storeToRefs(jobStore);

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

/** Total number of jobs matching the current filters. Doesn't necessarily match the total count
 * returned by the API because that count includes jobs from hidden tools, which we filter out client side.
 */
const totalJobCount = ref<number | undefined>(undefined);

/** Offset to request from the API. Tracked separately from `ScrollList`'s own offset (which is
 * derived from the *rendered* item count), because jobs from `HIDDEN_TOOL_IDS` are filtered out
 * client side. So for the same reason as using `totalJobCount`; we want to ensure we use an
 * offset that considers only non-hidden-tool jobs, so we don't have an infinite fetch due to
 * the mismatch between the API's total count and the number of jobs we actually render.
 */
const serverOffset = ref(0);

/** Changing this key remounts the `ScrollList`, so it drops the jobs it has loaded and
 * requests the first page again with the new filters. Name mode changes what the text matches. */
const filterKey = computed(() => {
    const text = filterText.value.trim();
    return text ? `${showToolNamesInJobPanel.value ? "name" : "id"}:${text}` : "";
});

/** IDs of jobs fetched for the *current* filters. `sortedStoredJobs` is a global, id-keyed
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
    serverOffset.value = 0;
    totalJobCount.value = undefined;
});

onUnmounted(stopRetainingCurrentJobs);

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

/** The jobs matching the current filters, kept up to date reactively as the store updates
 * (e.g. job state changes polled elsewhere), same as `sortedStoredInvocations` for invocations. */
const currentSortedJobs = computed(() => {
    return sortedStoredJobs.value.filter((job) => currentJobIds.value.has(job.id));
});

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

// Ensure any jobs added to the store while no filter is active are included in `currentJobIds`
// (these would be jobs not already included in the paginated set; think a job submitted while the panel is open)
watch(sortedStoredJobs, (jobs) => {
    if (filterText.value.trim()) {
        return;
    }
    for (const job of jobs) {
        if (!HIDDEN_TOOL_IDS.includes(job.tool_id) && !belongsToAnotherUser(job)) {
            addCurrentJob(job.id);
        }
    }
});

async function loadJobs(_offset: number, limit: number) {
    if (!currentUser.value || currentUser.value.isAnonymous) {
        return { items: [], total: 0 };
    }
    const requestGeneration = filterGeneration;
    if (showToolNamesInJobPanel.value) {
        await loadTools();
    }
    const extraProps: JobFetchExtraParams = {
        user_id: currentUser.value.id,
        ...jobsFilterParams(filterText.value, showToolNamesInJobPanel.value),
    };

    loading.value = true;
    let data: JobBaseModel[];
    let totalMatches: number;
    try {
        [data, totalMatches] = await fetchJobs(serverOffset.value, limit, extraProps);
    } finally {
        loading.value = false;
    }
    if (requestGeneration !== filterGeneration) {
        // Filters changed while loading; this page belongs to the discarded list.
        return { items: [], total: 0 };
    }
    serverOffset.value += data.length;

    const items = data.filter((job) => !HIDDEN_TOOL_IDS.includes(job.tool_id));
    for (const item of items) {
        addCurrentJob(item.id);
        jobStore.updateJob(item.id, item);
    }

    // `totalMatches` counts hidden-tool jobs too, which we are not showing.
    // Since the fetch gets all jobs, we set the job count as the number of jobs loaded so far if we got fewer than
    // the requested limit, otherwise we use the total matches count.
    totalJobCount.value = data.length < limit ? currentSortedJobs.value.length : totalMatches;
    return { items: currentSortedJobs.value, total: totalJobCount.value };
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
            <GCheckbox
                v-model="showToolNamesInJobPanel"
                v-g-tooltip.hover
                data-test-id="job-panel-name-mode-toggle"
                size="small"
                switch
                class="mx-2"
                title="Show/Search tool names instead of IDs">
                <span class="small unselectable">Tool Names</span>
            </GCheckbox>
        </template>

        <template v-slot:header>
            <FilterMenu
                v-model:filter-text="filterText"
                v-model:show-advanced="showAdvanced"
                name="Jobs"
                :placeholder="`search jobs by tool ${showToolNamesInJobPanel ? 'name' : 'ID'}`"
                :filter-class="showToolNamesInJobPanel ? JobsFiltersByName : JobsFiltersById"
                :loading="loading" />
        </template>

        <ScrollList
            v-show="!showAdvanced"
            :key="filterKey"
            :loader="loadJobs"
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
