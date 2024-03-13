<script setup lang="ts">
import HelpText from "@/components/Help/HelpText.vue";

interface Props {
    invocationId: string;
    invocationState: string;
}

defineProps<Props>();
</script>

<template>
    <HelpText :uri="`galaxy.invocations.states.${invocationState}`" :text="invocationState" />
</template>
