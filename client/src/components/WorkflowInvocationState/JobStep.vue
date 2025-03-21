<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BTab, BTabs } from "bootstrap-vue";
import Vue, { computed, ref, watch } from "vue";

import { GalaxyApi } from "@/api";
import { type JobBaseModel, type JobDetails } from "@/api/jobs";
import { getHeaderClass, iconClasses } from "@/composables/useInvocationGraph";
import { rethrowSimple } from "@/utils/simple-error";

import JobDetailsDisplayed from "../JobInformation/JobDetails.vue";
import LoadingSpan from "../LoadingSpan.vue";

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
        <LoadingSpan message="加载任务" />
    </BAlert>
    <BAlert v-else-if="!jobsDetails || !jobCount" variant="info" show> 找不到此步骤的任务。 </BAlert>
    <div v-else-if="jobCount === 1 && firstJob">
        <JobDetailsDisplayed :job="firstJob" />
    </div>
    <BTabs v-else vertical pills card nav-class="p-0" active-tab-class="p-0">
        <BTab
            v-for="job in jobsDetails"
            :key="job.id"
            data-description="工作流调用任务"
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
                <JobDetailsDisplayed :job="job" />
            </div>
        </BTab>
    </BTabs>
</template>
