<script setup lang="ts">
import HelpPopover from "./HelpPopover.vue";

interface Props {
    uri: string;
    text: string;
}

defineProps<Props>();
</script>

<template>
    <span>
        <HelpPopover
            :target="
                () => {
                    return $refs.helpTarget;
                }
            "
            :term="uri" />
        <span ref="helpTarget" class="help-text">{{ text }}</span>
    </span>
</template>

<style scoped>
/* Give visual indication of mouseover info */
.help-text {
    text-decoration-line: underline;
    text-decoration-style: dashed;
}
</style>
