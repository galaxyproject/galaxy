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

<style scoped lang="scss">
@import "theme/blue.scss";

.help-popover-content {
    font-size: $font-size-base;
    font-weight: normal;
    line-height: $line-height-base;
    text-transform: none;
}
</style>
