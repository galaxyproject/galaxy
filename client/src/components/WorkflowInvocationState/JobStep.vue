<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BTab, BTabs } from "bootstrap-vue";
import { computed, ref } from "vue";

import type { JobBaseModel, JobState } from "@/api/jobs";
import { getHeaderClass, iconClasses, statePlaceholders } from "@/composables/useInvocationGraph";

import GButton from "../BaseComponents/GButton.vue";
import JobDetailsDisplayed from "../JobInformation/JobDetails.vue";
import InvocationStepStateDisplay from "./InvocationStepStateDisplay.vue";

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

/** Currently selected/filtered job state */
const currentState = ref<JobState | null>(firstJob.value?.state || null);

function getIcon(job: JobBaseModel) {
    return iconClasses[job.state];
}

function getTabClass(job: JobBaseModel) {
    return {
        ...getHeaderClass(job.state),
        "d-flex": true,
        "text-center": true,
    };
}
</script>

<template>
    <BAlert v-if="!jobCount" variant="info" show> No jobs found for this step. </BAlert>
    <div v-else-if="jobCount === 1 && firstJob">
        <JobDetailsDisplayed :job-id="firstJob.id" />
    </div>
    <div v-else>
        <nav class="mb-2 p-2 d-flex flex-gapx-1">
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

        <BAlert v-if="!currentState" variant="info" show> Please select a job state to view jobs. </BAlert>
        <BTabs v-else lazy vertical pills card nav-class="p-0" active-tab-class="p-0">
            <BTab
                v-for="job in jobsByState[currentState]"
                :key="job.id"
                data-description="workflow invocation job"
                :title-item-class="getTabClass(job)"
                title-link-class="w-100">
                <template v-slot:title>
                    {{ job.state }}
                    <FontAwesomeIcon
                        v-if="getIcon(job)"
                        :class="getIcon(job)?.class"
                        :icon="getIcon(job)?.icon"
                        :spin="getIcon(job)?.spin" />
                </template>
                <div class="m-3">
                    <JobDetailsDisplayed :job-id="job.id" />
                </div>
            </BTab>
        </BTabs>
    </div>
</template>
