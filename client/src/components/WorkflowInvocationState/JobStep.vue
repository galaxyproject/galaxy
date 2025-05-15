<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BTab, BTabs } from "bootstrap-vue";
import { computed } from "vue";

import { type JobBaseModel } from "@/api/jobs";
import { getHeaderClass, iconClasses } from "@/composables/useInvocationGraph";

import JobDetailsDisplayed from "../JobInformation/JobDetails.vue";

interface Props {
    jobs: JobBaseModel[];
}

const props = withDefaults(defineProps<Props>(), {
    jobs: () => [],
});

const firstJob = computed(() => props.jobs[0]);
const jobCount = computed(() => props.jobs.length);

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
    <BTabs v-else lazy vertical pills card nav-class="p-0" active-tab-class="p-0">
        <BTab
            v-for="job in jobs"
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
            <div>
                <JobDetailsDisplayed :job-id="job.id" />
            </div>
        </BTab>
    </BTabs>
</template>
