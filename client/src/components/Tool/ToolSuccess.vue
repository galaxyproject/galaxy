<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useConfig } from "@/composables/config";
import { useJobStore } from "@/stores/jobStore";
import { useRouter } from "vue-router/composables";
import ToolEntryPoints from "@/components/ToolEntryPoints/ToolEntryPoints.vue";
import ToolRecommendation from "../ToolRecommendation.vue";
import ToolSuccessMessage from "./ToolSuccessMessage.vue";
import Webhook from "@/components/Common/Webhook.vue";

const { config } = useConfig(true);
const jobStore = useJobStore();
const router = useRouter();

const jobDef = computed(() => responseVal.value.jobDef);
const jobResponse = computed(() => responseVal.value.jobResponse);
const responseVal = computed(() => jobStore.getLatestResponse);
const showRecommendation = computed(() => config.value.enable_tool_recommendations);
const toolName = computed(() => responseVal.value.toolName);

/* lifecyle */
onMounted(() => {
    // no response means that no tool was run in this session i.e. no data in the store
    if (Object.keys(responseVal.value).length === 0) {
        router.push(`/`);
    }
});
</script>

<template>
    <section>
        <div v-if="jobResponse.produces_entry_points">
            <ToolEntryPoints v-for="job in jobResponse.jobs" :key="job.id" :job-id="job.id" />
        </div>
        <ToolSuccessMessage :job-response="jobResponse" :tool-name="toolName" />
        <Webhook type="tool" :tool-id="jobDef.tool_id" />
        <ToolRecommendation v-if="showRecommendation" :tool-id="jobDef.tool_id" />
    </section>
</template>
