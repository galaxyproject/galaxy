<script setup lang="ts">
import { BAlert } from "bootstrap-vue";

import GLink from "../BaseComponents/GLink.vue";

const props = defineProps<{
    invocationId: string;
    tooltip: string;
}>();
</script>

<template>
    <BAlert variant="info" show>
        <span v-localize>{{ props.tooltip }}</span>
        View the invocation
        <GLink :to="`/workflows/invocations/${props.invocationId}`">Overview</GLink>
        instead.
    </BAlert>
</template>
