<script setup lang="ts">
import { computed, ref } from "vue";

import type { ChatMessage, ExecutionState } from "./types";
import { hasCollapsedHistory, isDataAnalysisMessage } from "./utilities";

import AnalysisSteps from "./AnalysisSteps.vue";
import CollapsedHistoryMessages from "./CollapsedHistoryMessages.vue";
import ExecutedCode from "./ExecutedCode.vue";
import PyodideStatus from "./PyodideStatus.vue";
import Heading from "@/components/Common/Heading.vue";

const props = defineProps<{
    message: ChatMessage;
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

const toggled = ref(false);
</script>

<template>
    <div v-if="hasIntermediateDetails" class="intermediate-panel card mt-2">
        <div class="card-header p-3">
            <Heading h3 size="sm" separator :collapse="toggled ? 'closed' : 'open'" @click="toggled = !toggled">
                Intermediate steps
            </Heading>
        </div>
        <div v-if="!toggled" class="card-body">
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
    </div>
</template>

<style scoped lang="scss">
.intermediate-panel {
    .card-header {
        background-color: #f7f8fa;
        border-bottom: 1px solid #dfe3e6;
    }
}
</style>
