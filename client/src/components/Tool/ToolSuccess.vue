<script setup lang="ts">
import {
    faArrowCircleLeft,
    faArrowCircleRight,
    faCheck,
    faLightbulb,
    faWrench,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BDropdown } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import type { JobBaseModel, ShowFullJobResponse } from "@/api/jobs.js";
import { useConfig } from "@/composables/config";
import { useJobStore } from "@/stores/jobStore";

import LoadingSpan from "../LoadingSpan.vue";
import ToolRecommendation from "../ToolRecommendation.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GButtonGroup from "@/components/BaseComponents/GButtonGroup.vue";
import DetailBlock from "@/components/Common/DetailBlock.vue";
import Heading from "@/components/Common/Heading.vue";
import Webhook from "@/components/Common/Webhook.vue";
import JobHeader from "@/components/JobInformation/JobHeader.vue";
import JobInformation from "@/components/JobInformation/JobInformation.vue";
import ToolSuccessOutputs from "@/components/Tool/ToolSuccessOutputs.vue";
import ToolEntryPoints from "@/components/ToolEntryPoints/ToolEntryPoints.vue";

const { config } = useConfig(true);
const jobStore = useJobStore();
const { latestResponse } = storeToRefs(jobStore);
const router = useRouter();

const jobDef = computed(() => latestResponse.value?.jobDef);
const jobResponse = computed(() => latestResponse.value?.jobResponse);
const showRecommendation = computed(() => config.value.enable_tool_recommendations);
const nJobs = computed(() => (jobResponse.value && jobResponse.value.jobs ? jobResponse.value.jobs.length : 0));

// no data means that no tool was run in this session i.e. no data in the store
if (!latestResponse.value || Object.keys(latestResponse.value).length === 0) {
    router.push(`/`);
}

const viewedJob = ref<JobBaseModel | ShowFullJobResponse | null>(jobResponse.value?.jobs?.[0] || null);

watch(jobResponse, () => {
    viewedJob.value = jobResponse.value?.jobs?.[0] || null;
});

function navigateJob(direction: "previous" | "next") {
    const jobs = jobResponse.value?.jobs || [];
    if (!jobs.length) {
        return;
    }

    let currentIndex = jobs.findIndex((job) => job.id === viewedJob.value?.id);
    if (currentIndex === -1) {
        currentIndex = 0;
    }

    if (direction === "previous") {
        currentIndex = (currentIndex - 1 + jobs.length) % jobs.length;
    } else if (direction === "next") {
        currentIndex = (currentIndex + 1) % jobs.length;
    }
    viewedJob.value = jobs[currentIndex] || null;
}

const webhook = ref<InstanceType<typeof Webhook> | null>(null);
const webhookId = computed(() => webhook.value?.webhookId ?? null);
</script>

<template>
    <GAlert v-if="!jobResponse">
        <LoadingSpan message="Waiting on data" />
    </GAlert>
    <div v-else>
        <div v-if="nJobs > 1">
            <div class="d-flex justify-content-between">
                <div class="multi-job-header">
                    <span class="rounded px-2 py-1 tool-success-job-count">
                        <FontAwesomeIcon :icon="faCheck" fixed-width />
                        {{ nJobs }} Job{{ nJobs > 1 ? "s" : "" }} Submitted
                    </span>
                    <Heading :icon="faWrench" inline size="md">
                        {{ latestResponse?.toolName || "Multiple Jobs Run" }}
                    </Heading>
                </div>

                <div class="d-flex flex-gapx-1">
                    <GButtonGroup>
                        <GButton transparent @click="navigateJob('previous')">
                            <FontAwesomeIcon :icon="faArrowCircleLeft" />
                            Prev
                        </GButton>
                        <GButton transparent @click="navigateJob('next')">
                            <FontAwesomeIcon :icon="faArrowCircleRight" />
                            Next
                        </GButton>
                    </GButtonGroup>

                    <BDropdown class="job-selection-dropdown" size="sm" variant="link">
                        <BDropdownItem
                            v-for="job in jobResponse.jobs"
                            :key="job.id"
                            :active="viewedJob?.id === job.id"
                            @click="viewedJob = job">
                            {{ job.id }}
                        </BDropdownItem>
                    </BDropdown>
                </div>
            </div>

            <hr />
        </div>

        <JobHeader v-if="viewedJob" :job-id="viewedJob.id" :minimal="nJobs > 1" />

        <div v-if="viewedJob && jobResponse.produces_entry_points">
            <ToolEntryPoints :job-id="viewedJob.id" />
        </div>

        <JobInformation v-if="viewedJob" :job-id="viewedJob.id" collapsible />

        <ToolSuccessOutputs :job-response="jobResponse" />

        <DetailBlock v-if="jobDef" v-show="webhookId" :header-icon="faLightbulb" title="Before You Go">
            <Webhook ref="webhook" type="tool" :tool-id="jobDef.tool_id || undefined" />
        </DetailBlock>

        <ToolRecommendation v-if="showRecommendation && jobDef?.tool_id" :tool-id="jobDef.tool_id" />
    </div>
</template>

<style scoped lang="scss">
.multi-job-header {
    display: flex;
    align-items: center;
    gap: 0.85rem;
    flex-wrap: wrap;

    .tool-success-job-count {
        background-color: var(--color-blue-200);
    }
}

.job-selection-dropdown {
    :deep(.dropdown-menu) {
        overflow: auto;
        max-height: 50vh;
        min-width: 100%;
    }
}
</style>
