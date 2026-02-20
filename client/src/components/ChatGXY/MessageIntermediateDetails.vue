<script setup lang="ts">
import { computed } from "vue";

import type { ExecutionState, Message } from "./types";
import { hasCollapsedHistory, isDataAnalysisMessage } from "./utilities";

import AnalysisSteps from "./AnalysisSteps.vue";
import CollapsedHistoryMessages from "./CollapsedHistoryMessages.vue";
import ExecutedCode from "./ExecutedCode.vue";
import PyodideStatus from "./PyodideStatus.vue";

const props = defineProps<{
    message: Message;
    pyodideExecutions: Record<string, ExecutionState>;
}>();

const pyodideStateForMessage = computed<ExecutionState | undefined>(() => {
    const { pyodide_task } = props.message.agentResponse?.metadata || {};
    if (!pyodide_task) {
        return undefined;
    }
    const key = pyodide_task.task_id || props.message.id;
    return props.pyodideExecutions[key];
});

const hasIntermediateDetails = computed(() => {
    const metadata = props.message.agentResponse?.metadata;
    if (metadata?.executed_task?.code || metadata?.stdout || metadata?.stderr) {
        return true;
    }
    if (props.message.analysisSteps?.length) {
        return true;
    }
    if (pyodideStateForMessage.value) {
        return true;
    }
    return false;
});
</script>

<template>
    <details v-if="hasIntermediateDetails" class="intermediate-panel card mt-2">
        <summary class="text-muted">Intermediate steps</summary>
        <div class="card-body">
            <ExecutedCode
                v-if="props.message.agentResponse?.metadata?.executed_task?.code"
                :metadata="props.message.agentResponse?.metadata"
                class="mt-2" />

            <AnalysisSteps
                v-if="props.message.analysisSteps?.length"
                class="mt-2"
                :steps="props.message.analysisSteps" />

            <PyodideStatus
                v-if="props.message.role === 'assistant' && pyodideStateForMessage"
                :state="pyodideStateForMessage" />

            <CollapsedHistoryMessages
                v-if="!isDataAnalysisMessage(props.message) && hasCollapsedHistory(props.message)"
                :message="props.message"
                collapsible />
        </div>
    </details>
</template>

<style scoped lang="scss">
.intermediate-panel {
    summary {
        cursor: pointer;
        font-weight: 600;
    }
}
</style>
