<script setup lang="ts">
import { BAlert } from "bootstrap-vue";

import type { InvocationState } from "@/api/invocations";
import { withPrefix } from "@/utils/redirect";

import ExternalLink from "../ExternalLink.vue";
import HelpText from "../Help/HelpText.vue";

const props = defineProps<{
    invocationId: string;
    state?: InvocationState;
}>();
</script>

<template>
    <BAlert variant="secondary" show>
        <span v-if="props.state">
            This subworkflow is
            <HelpText :uri="`galaxy.invocations.states.${props.state}`" :text="props.state" />.
        </span>
        <ExternalLink :href="withPrefix(`/workflows/invocations/${props.invocationId}`)"> Click here </ExternalLink>
        to view this subworkflow in graph view.
    </BAlert>
</template>
