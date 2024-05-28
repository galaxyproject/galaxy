<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { computed } from "vue";
import { useRouter } from "vue-router/composables";

import { useConfig } from "@/composables/config";
import { useJobStore } from "@/stores/jobStore";

import LoadingSpan from "../LoadingSpan.vue";
import ToolRecommendation from "../ToolRecommendation.vue";
import ToolSuccessMessage from "./ToolSuccessMessage.vue";
import Webhook from "@/components/Common/Webhook.vue";
import ToolEntryPoints from "@/components/ToolEntryPoints/ToolEntryPoints.vue";

const { config } = useConfig(true);
const jobStore = useJobStore();
const router = useRouter();

const jobDef = computed(() => responseVal.value.jobDef);
const jobResponse = computed(() => responseVal.value.jobResponse);
const responseVal = computed(() => jobStore.getLatestResponse);
const showRecommendation = computed(() => config.value.enable_tool_recommendations);
const toolName = computed(() => responseVal.value.toolName);

// no data means that no tool was run in this session i.e. no data in the store
if (Object.keys(responseVal.value).length === 0) {
    router.push(`/`);
}
</script>

<template>
    <section>
        <BAlert v-if="!jobResponse" variant="info" show>
            <LoadingSpan message="Waiting on data" />
        </BAlert>
        <div v-else>
            <div v-if="jobResponse?.produces_entry_points">
                <ToolEntryPoints v-for="job in jobResponse.jobs" :key="job.id" :job-id="job.id" />
            </div>
            <ToolSuccessMessage :job-response="jobResponse" :tool-name="toolName" />
            <Webhook type="tool" :tool-id="jobDef.tool_id" />
            <ToolRecommendation v-if="showRecommendation" :tool-id="jobDef.tool_id" />
        </div>
    </section>
</template>
