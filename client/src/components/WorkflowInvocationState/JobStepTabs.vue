<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faClock } from "@fortawesome/free-regular-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BTab, BTabs } from "bootstrap-vue";
import Vue, { computed, ref, watch } from "vue";

import { GalaxyApi } from "@/api";
import { type JobBaseModel, type JobDetails } from "@/api/jobs";
import { getHeaderClass, iconClasses } from "@/composables/useInvocationGraph";
import { rethrowSimple } from "@/utils/simple-error";

import JobInformation from "../JobInformation/JobInformation.vue";
import JobParameters from "../JobParameters/JobParameters.vue";
import LoadingSpan from "../LoadingSpan.vue";
import UtcDate from "../UtcDate.vue";

library.add(faClock);

interface Props {
    jobs: JobBaseModel[];
}

const props = withDefaults(defineProps<Props>(), {
    jobs: () => [],
});

const loading = ref(true);
const initialLoading = ref(true);
const jobsDetails = ref<{ [key: string]: JobDetails }>({});

watch(
    () => props.jobs,
    async (propJobs: JobBaseModel[]) => {
        loading.value = true;
        for (const job of propJobs) {
            const { data, error } = await GalaxyApi().GET("/api/jobs/{job_id}", {
                params: {
                    path: { job_id: job.id },
                    query: { full: true },
                },
            });
            Vue.set(jobsDetails.value, job.id, data);
            if (error) {
                rethrowSimple(error);
            }
        }
        if (initialLoading.value) {
            initialLoading.value = false;
        }
        loading.value = false;
    },
    { immediate: true }
);

const firstJob = computed(() => Object.values(jobsDetails.value)[0]);
const jobCount = computed(() => Object.keys(jobsDetails.value).length);

function getIcon(job: JobDetails) {
    return iconClasses[job.state];
}

function getTabClass(job: JobDetails) {
    return {
        ...getHeaderClass(job.state),
        "d-flex": true,
        "text-center": true,
    };
}
</script>

<template>
    <BAlert v-if="initialLoading" variant="info" show>
        <LoadingSpan message="Loading Jobs" />
    </BAlert>
    <BAlert v-else-if="!jobsDetails || !jobCount" variant="info" show> No jobs found for this step. </BAlert>
    <div v-else-if="jobCount === 1 && firstJob">
        <JobInformation :job_id="firstJob.id" />
        <p></p>
        <JobParameters :job-id="firstJob.id" :include-title="false" />
    </div>
    <BTabs v-else vertical pills card nav-class="p-0">
        <BTab v-for="job in jobsDetails" :key="job.id" :title-item-class="getTabClass(job)" title-link-class="w-100">
            <template v-slot:title>
                {{ job.state }}
                <FontAwesomeIcon
                    v-if="getIcon(job)"
                    :class="getIcon(job)?.class"
                    :icon="getIcon(job)?.icon"
                    :spin="getIcon(job)?.spin" />
            </template>
            <div>
                <div class="d-flex justify-content-between">
                    <i>
                        <FontAwesomeIcon :icon="faClock" class="mr-1" />run
                        <UtcDate :date="job.create_time" mode="elapsed" />
                    </i>
                    <i>
                        <FontAwesomeIcon :icon="faClock" class="mr-1" />updated
                        <UtcDate :date="job.update_time" mode="elapsed" />
                    </i>
                </div>
                <hr class="w-100" />
                <JobInformation :job_id="job.id" />
                <p></p>
                <JobParameters :job-id="job.id" :include-title="false" />
            </div>
        </BTab>
    </BTabs>
</template>
