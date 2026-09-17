<script setup lang="ts">
import { faInfoCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref } from "vue";

import HelpPopover from "./HelpPopover.vue";

interface Props {
    uri: string;
    text?: string;
    forTitle?: boolean;
    /** Show an info icon that triggers the help popover */
    infoIcon?: boolean;
}

withDefaults(defineProps<Props>(), {
    text: "",
    forTitle: false,
    infoIcon: false,
});

const helpTarget = ref();
</script>

<template>
    <span class="help-text-wrapper">
        <HelpPopover v-if="helpTarget" :target="helpTarget" :term="uri" />
        <span v-if="text" ref="helpTarget" class="help-text" :class="{ 'title-help-text': forTitle }">{{ text }}</span>
        <span
            v-else-if="infoIcon"
            ref="helpTarget"
            class="help-info-icon"
            role="button"
            tabindex="0"
            aria-label="Help information">
            <FontAwesomeIcon :icon="faInfoCircle" />
        </span>
    </span>
</template>

<style scoped lang="scss">
@import "@/components/Help/help-text.scss";

.help-text-wrapper {
    display: inline;
}

.help-info-icon {
    cursor: help;
    opacity: 0.6;
    margin-left: 0.25rem;

    &:hover,
    &:focus {
        opacity: 1;
    }
}
</style>
