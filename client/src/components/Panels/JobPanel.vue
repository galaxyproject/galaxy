<script setup lang="ts">
import { faClock } from "@fortawesome/free-regular-svg-icons";
import { faHdd, faWrench } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router/composables";

import type { JobBaseModel } from "@/api/jobs";
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

/** Offset to request from the API. Tracked separately from the number of listed jobs,
 * because jobs from `HIDDEN_TOOL_IDS` are filtered out client side. */
const serverOffset = ref(0);
/** Number of jobs currently listed. */
const listedCount = ref(0);
/** Whether the API has run out of jobs to return. */
const allFetched = ref(false);

const filterText = ref("");
const showAdvanced = ref(false);
const loading = ref(false);

/** Changing this key remounts the `ScrollList`, so it drops the jobs it has loaded and
 * requests the first page again with the new filters. */
const filterKey = computed(() => filterText.value.trim());

watch(filterKey, () => {
    serverOffset.value = 0;
    listedCount.value = 0;
    allFetched.value = false;
});

async function loadJobs(_offset: number, limit: number) {
    if (!currentUser.value || currentUser.value.isAnonymous) {
        return { items: [], total: 0 };
    }
    const extraProps: Record<string, unknown> = {
        user_id: currentUser.value.id,
        ...jobsFilterParams(filterText.value),
    };

    const items: JobBaseModel[] = [];
    loading.value = true;
    try {
        // Keep requesting pages until we have something to list (a whole page can be
        // filtered out) or until the API runs out of jobs.
        while (!allFetched.value && items.length === 0) {
            const jobs = await jobStore.fetchAllJobs(serverOffset.value, limit, extraProps);
            serverOffset.value += jobs.length;
            allFetched.value = jobs.length < limit;
            items.push(...jobs.filter((job) => !HIDDEN_TOOL_IDS.includes(job.tool_id)));
        }
    } finally {
        loading.value = false;
    }
    loadHistories(items);
    listedCount.value += items.length;

    return { items, total: allFetched.value ? listedCount.value : listedCount.value + 1 };
}

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
