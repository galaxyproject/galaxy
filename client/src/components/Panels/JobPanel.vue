<script setup lang="ts">
import { faClock } from "@fortawesome/free-regular-svg-icons";
import { faHdd, faWrench } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router/composables";

import type { JobBaseModel } from "@/api/jobs";
import { fetchJobs } from "@/api/jobs";
import { jobsFilterParams, JobsFilters } from "@/components/Jobs/JobsFilters";
import { useHistoryStore } from "@/stores/historyStore";
import { useJobStore } from "@/stores/jobStore";
import { useUserStore } from "@/stores/userStore";

import FilterMenu from "@/components/Common/FilterMenu.vue";
import GCard from "@/components/Common/GCard.vue";
import Heading from "@/components/Common/Heading.vue";
import JobState from "@/components/JobStates/JobState.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";
import ScrollList from "@/components/ScrollList/ScrollList.vue";

const HIDDEN_TOOL_IDS = ["__DATA_FETCH__"];

interface Props {
    inPanel?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    inPanel: false,
});

const currentUser = computed(() => useUserStore().currentUser);

const jobStore = useJobStore();
const { sortedStoredJobs } = storeToRefs(jobStore);

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
 * requests the first page again with the new filters. */
const filterKey = computed(() => filterText.value.trim());

/** IDs of jobs fetched for the *current* filters. `sortedStoredJobs` is a global, id-keyed
 * cache shared across the whole app, so it can hold jobs from a previous filter. This set
 * scopes the list back down to just what matches the current filters. */
const currentJobIds = ref(new Set<string>());

watch(filterKey, () => {
    currentJobIds.value = new Set();
    serverOffset.value = 0;
    totalJobCount.value = undefined;
});

/** The jobs matching the current filters, kept up to date reactively as the store updates
 * (e.g. job state changes polled elsewhere), same as `sortedStoredInvocations` for invocations. */
const currentSortedJobs = computed(() => {
    return sortedStoredJobs.value.filter((job) => currentJobIds.value.has(job.id));
});

async function loadJobs(_offset: number, limit: number) {
    if (!currentUser.value || currentUser.value.isAnonymous) {
        return { items: [], total: 0 };
    }
    const extraProps: Record<string, unknown> = {
        user_id: currentUser.value.id,
        ...jobsFilterParams(filterText.value),
    };

    loading.value = true;
    let data: JobBaseModel[];
    let totalMatches: number;
    try {
        [data, totalMatches] = await fetchJobs(serverOffset.value, limit, extraProps);
    } finally {
        loading.value = false;
    }
    serverOffset.value += data.length;

    const items = data.filter((job) => !HIDDEN_TOOL_IDS.includes(job.tool_id));
    for (const item of items) {
        jobStore.updateJob(item.id, item);
        currentJobIds.value.add(item.id);
    }

    // `totalMatches` counts hidden-tool jobs too, which we are not showing.
    // Since the fetch gets all jobs, we set the job count as the number of jobs loaded so far if we got fewer than
    // the requested limit, otherwise we use the total matches count.
    totalJobCount.value = data.length < limit ? currentSortedJobs.value.length : totalMatches;
    loadHistories(items);
    return { items: currentSortedJobs.value, total: totalJobCount.value };
}

// TODO: Re-evaluate if we need this? This is a lot of histories being fetched...
/** Load the histories of the given jobs, if not already cached, so their names can be displayed */
function loadHistories(jobs: JobBaseModel[]) {
    const historyStore = useHistoryStore();
    const historyIds = new Set<string>();
    jobs.forEach((job) => job.history_id && historyIds.add(job.history_id));
    historyIds.forEach(
        (historyId) => historyStore.getHistoryById(historyId) || historyStore.loadHistoryById(historyId),
    );
}

function historyName(historyId: string) {
    const historyStore = useHistoryStore();
    return historyStore.getHistoryNameById(historyId);
}

const route = useRoute();
const router = useRouter();

const currentItemId = computed(() => {
    const match = route.path.match(/\/jobs\/([a-zA-Z0-9]+)\/view/);
    return match ? match[1] : undefined;
});

function cardClicked(job: JobBaseModel) {
    router.push(`/jobs/${job.id}/view`);
}
</script>

<template>
    <ActivityPanel title="Jobs">
        <template v-slot:header>
            <FilterMenu
                name="Jobs"
                placeholder="search jobs"
                :filter-class="JobsFilters"
                :filter-text.sync="filterText"
                :loading="loading"
                :show-advanced.sync="showAdvanced" />
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
            name="job"
            name-plural="jobs"
            :load-disabled="!currentUser || currentUser.isAnonymous">
            <template v-slot:item="{ item: job }">
                <GCard
                    :id="`job-${job.id}`"
                    clickable
                    button
                    :current="job.id === currentItemId"
                    :active="job.id === currentItemId"
                    :title="job.tool_id"
                    :title-icon="{ icon: faWrench }"
                    :title-n-lines="2"
                    title-size="text"
                    :update-time="job.update_time"
                    :update-time-icon="faClock"
                    @click="() => cardClicked(job)">
                    <template v-slot:description>
                        <Heading class="m-0" size="text">
                            <FontAwesomeIcon :icon="faHdd" fixed-width />

                            <small v-if="job.history_id" class="text-muted truncate-n-lines two-lines">
                                {{ historyName(job.history_id) }}
                            </small>
                        </Heading>
                    </template>
                    <template v-slot:badges>
                        <JobState :job="job" />
                    </template>
                </GCard>
            </template>
        </ScrollList>
    </ActivityPanel>
</template>

<style scoped lang="scss">
.truncate-n-lines {
    display: -webkit-box;
    -webkit-box-orient: vertical;
    overflow: hidden;
    word-break: break-word;
    overflow-wrap: break-word;
    &.two-lines {
        -webkit-line-clamp: 2;
        line-clamp: 2;
    }
}
</style>
