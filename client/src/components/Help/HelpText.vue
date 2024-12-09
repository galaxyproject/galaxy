<script setup lang="ts">
import HelpPopover from "./HelpPopover.vue";

interface Props {
    uri: string;
    text: string;
    forTitle?: boolean;
}

withDefaults(defineProps<Props>(), {
    forTitle: false,
});
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
        <span ref="helpTarget" class="help-text" :class="{ 'title-help-text': forTitle }">{{ text }}</span>
    </span>
</template>

<style scoped>
/* Give visual indication of mouseover info */
.help-text {
    text-decoration-line: underline;
    text-decoration-style: dashed;
}
.title-help-text {
    text-decoration-thickness: 1px;
}
</style>
