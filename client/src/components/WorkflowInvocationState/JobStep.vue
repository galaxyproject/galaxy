<script setup lang="ts">
import { BAlert, BPagination } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import type { JobBaseModel, JobState } from "@/api/jobs";
import { statePlaceholders } from "@/composables/useInvocationGraph";

import GButton from "../BaseComponents/GButton.vue";
import JobDetailsDisplayed from "../JobInformation/JobDetails.vue";
import InvocationStepStateDisplay from "./InvocationStepStateDisplay.vue";
import JobStepJobs from "./JobStepJobs.vue";

const PER_PAGE = 10;

interface Props {
    jobs: JobBaseModel[];
}

const props = withDefaults(defineProps<Props>(), {
    jobs: () => [],
});

const firstJob = computed(() => props.jobs[0]);
const jobCount = computed(() => props.jobs.length);

/** Jobs grouped by their state */
const jobsByState = computed(() => {
    const jobsMap: { [key: string]: JobBaseModel[] } = {};
    props.jobs.forEach((job) => {
        if (!jobsMap[job.state]) {
            jobsMap[job.state] = [];
        }
        jobsMap[job.state]?.push(job);
    });
    return jobsMap as Record<JobState, JobBaseModel[]>;
});

/** Jobs in the currently selected state */
const currentStateJobs = computed(() => {
    if (!currentState.value || !jobsByState.value[currentState.value]) {
        return [];
    }
    return jobsByState.value[currentState.value].slice().sort((a, b) => {
        let compare = 0;
        compare = new Date(a.update_time).getTime() - new Date(b.update_time).getTime();

        return sortDesc.value ? -compare : compare;
    });
});

/** Currently selected/filtered job state */
const currentState = ref<JobState | null>(firstJob.value?.state || null);

const currentPage = ref(1);
const sortDesc = ref(true);

watch(
    () => currentState.value,
    () => {
        currentPage.value = 1;
    },
);

// For a running workflow, if the available states change, ensure the current state is still valid
watch(
    () => Object.keys(jobsByState.value),
    (newStates) => {
        if (currentState.value && !newStates.includes(currentState.value)) {
            currentState.value = (newStates[0] as JobState) || null;
        }
    },
);
</script>

<template>
    <BAlert v-if="!jobCount" variant="info" show> No jobs found for this step. </BAlert>
    <div v-else-if="jobCount === 1 && firstJob">
        <JobDetailsDisplayed :job-id="firstJob.id" />
    </div>
    <div v-else>
        <div class="mb-2 p-2 d-flex justify-content-between align-items-center flex-wrap">
            <nav class="d-flex flex-gapx-1">
                <GButton
                    v-for="(stateJobs, state) in jobsByState"
                    :key="state"
                    outline
                    color="blue"
                    :title="`Click to view ${statePlaceholders[state] || state} jobs`"
                    :pressed="currentState === state"
                    @click="currentState = state">
                    <InvocationStepStateDisplay :state="state" :job-count="stateJobs.length" />
                </GButton>
            </nav>

            <div>
                <BPagination
                    v-if="currentState && jobsByState[currentState].length > PER_PAGE"
                    v-model="currentPage"
                    class="justify-content-md-center m-0"
                    size="sm"
                    :per-page="PER_PAGE"
                    :total-rows="jobsByState[currentState].length" />
            </div>
        </div>

        <BAlert v-if="!currentState" variant="info" show> Please select a job state to view jobs. </BAlert>
        <JobStepJobs
            v-else
            :jobs="currentStateJobs"
            :current-page.sync="currentPage"
            :sort-desc.sync="sortDesc"
            :per-page="PER_PAGE" />
    </div>
</template>
