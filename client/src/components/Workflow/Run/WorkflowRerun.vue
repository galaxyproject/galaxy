<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { Toast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";
import { useInvocationStore } from "@/stores/invocationStore";

import WorkflowRun from "./WorkflowRun.vue";

const props = defineProps<{
    invocationId: string;
}>();

const historyStore = useHistoryStore();
const invocationStore = useInvocationStore();

const ready = ref(false);

const requestData = computed(() => invocationStore.getInvocationRequestById(props.invocationId));

watch(
    requestData,
    async (rerunData) => {
        if (rerunData && !ready.value) {
            // switch to the history with the original workflow inputs first, then render `WorkflowRun`
            await historyStore.setCurrentHistory(rerunData.history_id);

            // if we were unable to set the history, we need to show an error
            if (historyStore.currentHistoryId !== rerunData.history_id) {
                Toast.error("Unable to switch to the history with the original workflow inputs.");
            }
            ready.value = true;
        }
    },
    { immediate: true }
);
</script>

<template>
    <WorkflowRun
        v-if="ready && requestData"
        :workflow-id="requestData.workflow_id"
        :instance="requestData.instance"
        :request-state="requestData.inputs"
        prefer-simple-form
        is-rerun
        :simple-form-use-job-cache="requestData.use_cached_job" />
</template>
