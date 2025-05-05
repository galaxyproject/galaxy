<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { computed } from "vue";

import { type WorkflowInvocationElementView } from "@/api/invocations";
import { useWorkflowInstance } from "@/composables/useWorkflowInstance";
import { withPrefix } from "@/utils/redirect";

import ExternalLink from "../ExternalLink.vue";
import HelpText from "../Help/HelpText.vue";
import InvocationGraph from "../Workflow/Invocation/Graph/InvocationGraph.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import InvocationMessage from "@/components/WorkflowInvocationState/InvocationMessage.vue";

interface Props {
    invocation: WorkflowInvocationElementView;
    invocationAndJobTerminal: boolean;
    isFullPage?: boolean;
    isSubworkflow?: boolean;
}

const props = defineProps<Props>();

const { workflow, loading, error } = useWorkflowInstance(props.invocation.workflow_id);

const uniqueMessages = computed(() => {
    const messages = props.invocation.messages || [];
    const uniqueMessagesSet = new Set(messages.map((message) => JSON.stringify(message)));
    return Array.from(uniqueMessagesSet).map((message) => JSON.parse(message)) as typeof messages;
});
</script>

<template>
    <div class="mb-3 workflow-invocation-state-component">
        <BAlert v-if="isSubworkflow" variant="secondary" show>
            This subworkflow is
            <HelpText :uri="`galaxy.invocations.states.${invocation.state}`" :text="invocation.state" />.
            <ExternalLink :href="withPrefix(`/workflows/invocations/${invocation.id}`)"> Click here </ExternalLink>
            to view this subworkflow in graph view.
        </BAlert>
        <div v-if="uniqueMessages.length" class="d-flex align-items-center">
            <InvocationMessage
                v-for="message in uniqueMessages"
                :key="message.reason"
                class="steps-progress my-1 w-100"
                :invocation-message="message"
                :invocation="invocation">
            </InvocationMessage>
        </div>
        <!-- Once the workflow for the invocation has been loaded, display the graph -->
        <BAlert v-if="loading" variant="info" show>
            <LoadingSpan message="Loading workflow..." />
        </BAlert>
        <BAlert v-else-if="error" variant="danger" show>
            {{ error }}
        </BAlert>
        <div v-else-if="workflow && !isSubworkflow">
            <InvocationGraph
                class="mt-1"
                data-description="workflow invocation graph"
                :invocation="invocation"
                :workflow="workflow"
                :is-terminal="invocationAndJobTerminal"
                :is-full-page="isFullPage"
                :show-minimap="isFullPage" />
        </div>
        <BAlert v-else-if="!workflow" variant="info" show> No workflow found for this invocation. </BAlert>
    </div>
</template>
