<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { Toast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";
import { useInvocationStore } from "@/stores/invocationStore";
import { errorMessageAsString } from "@/utils/simple-error.js";

import WorkflowRun from "./WorkflowRun.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const props = defineProps<{
    invocationId: string;
}>();

const historyStore = useHistoryStore();
const invocationStore = useInvocationStore();

const ready = ref(false);

const requestData = computed(() => invocationStore.getInvocationRequestById(props.invocationId));
const requestError = computed(() => invocationStore.getInvocationRequestByIdError(props.invocationId));

watch(
    requestData,
    async (rerunData) => {
        if (rerunData && !ready.value) {
            // switch to the history with the original workflow inputs first, then render `WorkflowRun`
            try {
                await historyStore.setCurrentHistory(rerunData.history_id);
                // The store can skip the switch if another history switch is in progress.
                if (historyStore.currentHistoryId !== rerunData.history_id) {
                    Toast.error("Unable to switch to the history with the original workflow inputs.");
                }
            } catch (e) {
                Toast.error(
                    `Unable to switch to the history with the original workflow inputs. ${errorMessageAsString(e)}`,
                );
            }
            ready.value = true;
        }
    },
    { immediate: true },
);
</script>

<template>
    <GAlert v-if="requestError" variant="danger">
        Unable to load workflow rerun data: {{ errorMessageAsString(requestError) }}
    </GAlert>
    <WorkflowRun
        v-else-if="ready && requestData"
        :workflow-id="requestData.workflow_id"
        :instance="requestData.instance"
        :request-state="requestData.inputs"
        prefer-simple-form
        is-rerun
        :simple-form-use-job-cache="requestData.use_cached_job" />
    <LoadingSpan v-else message="Loading workflow rerun data" />
</template>
