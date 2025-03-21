<script setup lang="ts">
import { onMounted } from "vue";

import type { WorkflowInvocation } from "@/api/invocations";
import { useHistoryStore } from "@/stores/historyStore";
import Webhooks from "@/utils/webhooks";
import { startWatchingHistory } from "@/watch/watchHistory";

import GridInvocation from "@/components/Grid/GridInvocation.vue";
import WorkflowInvocationState from "@/components/WorkflowInvocationState/WorkflowInvocationState.vue";

const props = defineProps<{
    workflowName: string;
    invocations: WorkflowInvocation[];
}>();

onMounted(() => {
    new Webhooks.WebhookView({
        type: "workflow",
        toolId: null,
        toolVersion: null,
    });
    startWatchingHistory();
});

const historyStore = useHistoryStore();

const targetHistories = props.invocations.reduce((histories, invocation) => {
    if (invocation.history_id && !histories.includes(invocation.history_id)) {
        histories.push(invocation.history_id);
    }
    return histories;
}, [] as string[]);
const wasNewHistoryTarget =
    props.invocations.length > 0 &&
    !!props.invocations[0]?.history_id &&
    historyStore.currentHistoryId !== props.invocations[0].history_id;
</script>
<template>
    <div>
        <div v-if="props.invocations.length > 1" class="donemessagelarge">
            成功调用工作流 <b>{{ props.workflowName }}</b>
            <em> - {{ props.invocations.length }} 次</em>。
            <span v-if="targetHistories.length > 1">
                此工作流将在多个历史记录中生成结果。您可以在
                <router-link to="/histories/view_multiple">历史记录多视图</router-link>中查看进度。
            </span>
        </div>
        <GridInvocation v-if="props.invocations.length > 1" :invocations-list="props.invocations" />
        <WorkflowInvocationState
            v-else-if="props.invocations.length === 1 && props.invocations[0]"
            :invocation-id="props.invocations[0].id"
            :new-history-target="wasNewHistoryTarget"
            is-full-page
            success />
        <div id="webhook-view"></div>
    </div>
</template>
