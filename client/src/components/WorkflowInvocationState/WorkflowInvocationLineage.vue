<script setup lang="ts">
import type { WorkflowInvocationElementView } from "@/api/invocations";

import GAlert from "@/components/BaseComponents/GAlert.vue";

defineProps<{
    invocation: Pick<WorkflowInvocationElementView, "rerun_of_invocation_id" | "latest_rerun_invocation_id">;
}>();
</script>

<template>
    <div v-if="invocation.rerun_of_invocation_id || invocation.latest_rerun_invocation_id">
        <GAlert v-if="invocation.rerun_of_invocation_id" variant="info">
            This invocation is a rerun of an earlier invocation.
            <RouterLink
                :to="`/workflows/invocations/${invocation.rerun_of_invocation_id}`"
                data-description="source invocation link">
                View source invocation
            </RouterLink>
        </GAlert>
        <GAlert v-if="invocation.latest_rerun_invocation_id" variant="info">
            A newer rerun of this invocation exists.
            <RouterLink
                :to="`/workflows/invocations/${invocation.latest_rerun_invocation_id}`"
                data-description="latest rerun invocation link">
                View latest rerun
            </RouterLink>
        </GAlert>
    </div>
</template>
