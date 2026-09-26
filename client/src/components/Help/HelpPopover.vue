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
    <!-- setting font-size:0 so this span doesn't affect the spacing in the parent component -->
    <Popper v-if="target" style="font-size: 0" :reference-el="target" mode="light">
        <HelpTerm :term="term" class="p-2 help-popover-content" />
    </Popper>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.help-popover-content {
    font-size: $font-size-base;
    font-weight: normal;
    line-height: $line-height-base;
    text-transform: none;
}
</style>
