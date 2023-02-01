<script setup lang="ts">
// import FormBoolean from "./Elements/FormBoolean.vue";
import { computed, onMounted } from "vue";

import type { ComputedRef } from "vue";
import { useJobStore } from "@/stores/jobStore";
import { useRouter } from "vue-router/composables";
import { getGalaxyInstance } from "@/app";
import ToolEntryPoints from "@/components/ToolEntryPoints/ToolEntryPoints.vue";
import ToolSuccessMessage from "./ToolSuccessMessage.vue";
import ToolRecommendation from "../ToolRecommendation.vue";
import Webhook from "@/components/Common/Webhook.vue";

const jobStore = useJobStore();
const router = useRouter();

/* interfaces */
interface Job {
    id: string;
}
interface JobDef {
    tool_id: string;
}
interface JobResponse {
    produces_entry_points: boolean;
    jobs: Array<Job>;
}
interface ResponseVal {
    jobDef: JobDef;
    jobResponse: JobResponse;
    toolName: string;
}

/* props */
const props = defineProps({
    jobId: {
        type: String,
        required: true,
    },
});

const responseVal: ComputedRef<ResponseVal> = computed(() => jobStore.getResponseForJobId(props.jobId));

/* lifecyle */
onMounted(() => {
    // no response means no tool produced this job in this session (nothing in store)
    if (!responseVal.value) {
        router.push(`/jobs/${props.jobId}/view`);
    }
});

const jobDef: ComputedRef<JobDef> = computed(() => responseVal.value.jobDef);
const jobResponse: ComputedRef<JobResponse> = computed(() => responseVal.value.jobResponse);
const toolName: ComputedRef<string> = computed(() => responseVal.value.toolName);

// getGalaxyInstance is not reactive
const configEnableRecommendations = getGalaxyInstance().config.enable_tool_recommendations;
const showRecommendation: boolean = [true, "true"].includes(configEnableRecommendations);
</script>

<template>
    <section v-if="responseVal">
        <div v-if="jobResponse.produces_entry_points">
            <ToolEntryPoints v-for="job in jobResponse.jobs" :key="job.id" :job-id="job.id" />
        </div>
        <ToolSuccessMessage :job-def="jobDef" :job-response="jobResponse" :tool-name="toolName" />
        <Webhook type="tool" :tool-id="jobDef.tool_id" />
        <ToolRecommendation v-if="showRecommendation" :tool-id="jobDef.tool_id" />
    </section>
</template>
