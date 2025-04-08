<script setup lang="ts">
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { faPlay, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

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

withDefaults(defineProps<Props>(), {
    title: "",
    wait: false,
    tooltip: "",
    disabled: false,
    size: "medium",
    color: "blue",
    icon: undefined,
});
</script>

<template>
    <GButton
        tooltip
        tooltip-placement="bottom"
        :color="color"
        class="d-flex flex-nowrap align-items-center text-nowrap"
        :title="tooltip"
        :disabled="wait ?? disabled"
        :size="size"
        @click="$emit('onClick')">
        <FontAwesomeIcon v-if="wait" :icon="faSpinner" fixed-width spin />
        <FontAwesomeIcon v-else :icon="!icon ? faPlay : icon" fixed-width />
        <span v-if="title" class="ml-1">{{ title }}</span>
    </GButton>
</template>
