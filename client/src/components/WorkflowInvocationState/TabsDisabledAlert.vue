<script setup lang="ts">
import GLink from "../BaseComponents/GLink.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";

const props = defineProps<{
    invocationId: string;
    tooltip: string;
}>();
</script>

<template>
    <GAlert variant="info" show>
        <span v-localize>{{ props.tooltip }}</span>
        View the invocation
        <GLink :to="`/workflows/invocations/${props.invocationId}`">Overview</GLink>
        instead.
    </GAlert>
</template>
