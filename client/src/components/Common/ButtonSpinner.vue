<script setup lang="ts">
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { faPlay, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import type { ComponentColor, ComponentSize } from "@/components/BaseComponents/componentVariants";

import GButton from "@/components/BaseComponents/GButton.vue";

interface Props {
    title?: string;
    wait?: boolean;
    tooltip?: string;
    disabled?: boolean;
    size?: ComponentSize;
    color?: ComponentColor;
    icon?: IconDefinition;
}

const props = withDefaults(defineProps<Props>(), {
    title: "",
    wait: false,
    tooltip: "",
    disabled: false,
    size: "medium",
    color: "blue",
    icon: undefined,
});

const currentTitle = computed(() => (props.wait ? "Please wait..." : props.tooltip));
</script>

<template>
    <GButton
        tooltip
        tooltip-placement="bottom"
        :color="props.color"
        :title="currentTitle"
        :disabled="props.wait || props.disabled"
        :size="props.size"
        @click="$emit('onClick')">
        <FontAwesomeIcon v-if="wait" :icon="faSpinner" fixed-width spin />
        <FontAwesomeIcon v-else :icon="!props.icon ? faPlay : props.icon" fixed-width />
        <span v-if="title">{{ title }}</span>
    </GButton>
</template>
