<script setup lang="ts">
import { faRedo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, toRef } from "vue";
import { useRoute } from "vue-router/composables";

import { useJobDetails } from "@/composables/jobDetails.js";
import { useToolStore } from "@/stores/toolStore";

import GButton from "../BaseComponents/GButton.vue";

const route = useRoute();

const props = defineProps<{
    jobId: string;
    outline?: boolean;
}>();

const { job } = useJobDetails(toRef(props, "jobId"));
const toolStore = useToolStore();

const rerunUrl = computed(() => `/?job_id=${props.jobId}`);

const canRerunJob = computed(() => job.value && toolStore.getToolForId(job.value.tool_id)?.is_workflow_compatible);
</script>

<template>
    <GButton
        v-if="canRerunJob"
        title="Run Job Again"
        size="small"
        color="blue"
        :outline="props.outline"
        :transparent="!props.outline"
        :pressed="route.fullPath === rerunUrl"
        :to="rerunUrl">
        <FontAwesomeIcon fixed-width :icon="faRedo" />
        <span class="text-nowrap">Run again</span>
    </GButton>
</template>
