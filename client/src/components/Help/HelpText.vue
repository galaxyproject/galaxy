<script setup lang="ts">
import { ref } from "vue";

import HelpPopover from "./HelpPopover.vue";

interface Props {
    uri: string;
    text: string;
    forTitle?: boolean;
}

withDefaults(defineProps<Props>(), {
    forTitle: false,
});

const helpTarget = ref();
</script>

<template>
    <span>
        <HelpPopover :target="helpTarget" :term="uri" />
        <span ref="helpTarget" class="help-text" :class="{ 'title-help-text': forTitle }">{{ text }}</span>
    </span>
</template>

<style scoped src="@/components/Help/help-text.scss" />
