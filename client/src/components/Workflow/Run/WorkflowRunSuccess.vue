<script setup lang="ts">
import { onMounted } from "vue";

import type { WorkflowInvocation } from "@/api/invocations";
import { refreshContentsWrapper } from "@/utils/data";
import Webhooks from "@/utils/webhooks";

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
    refreshContentsWrapper();
});

const targetHistories = props.invocations.reduce((histories, invocation) => {
    if (invocation.history_id && !histories.includes(invocation.history_id)) {
        histories.push(invocation.history_id);
    }
    return histories;
}, [] as string[]);
</script>

<template>
    <div>
        <div v-if="props.invocations.length > 1" class="donemessagelarge">
            Successfully invoked workflow <b>{{ props.workflowName }}</b>
            <em> - {{ props.invocations.length }} times</em>.
            <span v-if="targetHistories.length > 1">
                This workflow will generate results in multiple histories. You can observe progress in the
                <router-link to="/histories/view_multiple">history multi-view</router-link>.
            </span>
        </div>
        <GridInvocation v-if="props.invocations.length > 1" :invocations-list="props.invocations" />
        <WorkflowInvocationState
            v-else-if="props.invocations.length === 1 && props.invocations[0]"
            :invocation-id="props.invocations[0].id"
            is-full-page
            success />
        <div id="webhook-view"></div>
    </div>
</template>
