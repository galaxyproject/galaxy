<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useJobStore } from "@/stores/jobStore";
import { useRouter } from "vue-router/composables";
import { getGalaxyInstance } from "@/app";
import ToolEntryPoints from "@/components/ToolEntryPoints/ToolEntryPoints.vue";
import ToolSuccessMessage from "./ToolSuccessMessage.vue";
import ToolRecommendation from "../ToolRecommendation.vue";
import Webhook from "@/components/Common/Webhook.vue";

const jobStore = useJobStore();
const router = useRouter();

const responseVal = computed(() => jobStore.getLatestResponse);

/* lifecyle */
onMounted(() => {
    // no response means no ToolForm ran in this session (nothing in store)
    if (Object.keys(responseVal.value).length === 0) {
        router.push(`/`);
    }
});

const jobDef = computed(() => responseVal.value.jobDef);
const jobResponse = computed(() => responseVal.value.jobResponse);
const toolName = computed(() => responseVal.value.toolName);

// getGalaxyInstance is not reactive
const configEnableRecommendations = getGalaxyInstance().config.enable_tool_recommendations;
const showRecommendation: boolean = [true, "true"].includes(configEnableRecommendations);
</script>

<template>
    <section v-if="jobResponse && jobDef">
        <div v-if="jobResponse.produces_entry_points">
            <ToolEntryPoints v-for="job in jobResponse.jobs" :key="job.id" :job-id="job.id" />
        </div>
        <ToolSuccessMessage :job-def="jobDef" :job-response="jobResponse" :tool-name="toolName" />
        <Webhook type="tool" :tool-id="jobDef.tool_id" />
        <ToolRecommendation v-if="showRecommendation" :tool-id="jobDef.tool_id" />
    </section>
</template>
