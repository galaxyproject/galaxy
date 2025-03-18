<script setup lang="ts">
import HelpTerm from "./HelpTerm.vue";
import Popper from "@/components/Popper/Popper.vue";

interface Props {
    target: HTMLElement;
    term: string;
}

defineProps<Props>();
</script>

<template>
    <Popper v-if="target" :reference-el="target" mode="light">
        <HelpTerm :term="term" class="p-2 help-popover-content" />
    </Popper>
</template>

<style scoped>
.help-popover-content {
    font-size: 1rem; /* Reset to default text size */
    font-weight: normal;
    line-height: 1.5;
    text-transform: none;
}
</style>
