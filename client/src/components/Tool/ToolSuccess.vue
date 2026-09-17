<script setup lang="ts">
import { faLightbulb } from "@fortawesome/free-solid-svg-icons";
import { BPagination } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import type { JobBaseModel, ShowFullJobResponse } from "@/api/jobs.js";
import { useConfig } from "@/composables/config";
import { useJobStore } from "@/stores/jobStore";

import LoadingSpan from "../LoadingSpan.vue";
import ToolRecommendation from "../ToolRecommendation.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";
import DetailBlock from "@/components/Common/DetailBlock.vue";
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

const currentIndex = ref(0);
// BPagination is 1-indexed; bridge to the 0-indexed currentIndex.
const paginationPage = computed<number>({
    get: () => currentIndex.value + 1,
    set: (val: number) => {
        currentIndex.value = val - 1;
    },
});

watch(jobResponse, () => {
    currentIndex.value = 0;
});

const viewedJob = computed<JobBaseModel | ShowFullJobResponse | null>(
    () => jobResponse.value?.jobs?.[currentIndex.value] ?? jobResponse.value?.jobs?.[0] ?? null,
);

const webhook = ref<InstanceType<typeof Webhook> | null>(null);
const webhookId = computed(() => webhook.value?.webhookId ?? null);
</script>

<template>
    <GAlert v-if="!jobResponse">
        <LoadingSpan message="Waiting on data" />
    </GAlert>
    <div v-else>
        <template v-if="viewedJob">
            <JobHeader :job-id="viewedJob.id">
                <template v-slot:pagination>
                    <BPagination
                        v-if="nJobs > 1"
                        v-model="paginationPage"
                        :total-rows="nJobs"
                        :per-page="1"
                        size="sm"
                        :limit="3"
                        first-number
                        last-number
                        hide-goto-end-buttons
                        class="mb-0 unselectable" />
                </template>
            </JobHeader>

            <div v-if="jobResponse.produces_entry_points">
                <ToolEntryPoints :job-id="viewedJob.id" />
            </div>

            <JobInformation :job-id="viewedJob.id" collapsible />
        </template>

        <ToolSuccessOutputs :job-response="jobResponse" />

        <DetailBlock v-if="jobDef" v-show="webhookId" :header-icon="faLightbulb" title="Before You Go">
            <Webhook ref="webhook" type="tool" :tool-id="jobDef.tool_id || undefined" />
        </DetailBlock>

        <ToolRecommendation v-if="showRecommendation && jobDef?.tool_id" :tool-id="jobDef.tool_id" />
    </div>
</template>
