<script setup lang="ts">
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { faPlay, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";

interface Props {
    title?: string;
    wait?: boolean;
    tooltip?: string;
    disabled?: boolean;
    size?: string;
    variant?: string;
    icon?: IconDefinition;
}

withDefaults(defineProps<Props>(), {
    title: "",
    wait: false,
    tooltip: "",
    disabled: false,
    size: "md",
    variant: "primary",
    icon: undefined,
});
</script>

<template>
    <BButton
        v-if="wait"
        v-b-tooltip.hover.bottom
        disabled
        :size="size"
        variant="info"
        title="Please Wait..."
        class="d-flex flex-nowrap align-items-center text-nowrap">
        <FontAwesomeIcon :icon="faSpinner" fixed-width spin />
        <span v-if="title" class="ml-1">{{ title }}</span>
    </BButton>
    <BButton
        v-else
        v-b-tooltip.hover.bottom
        :variant="variant"
        class="d-flex flex-nowrap align-items-center text-nowrap"
        :title="tooltip"
        :disabled="disabled"
        :size="size"
        @click="$emit('onClick')">
        <FontAwesomeIcon :icon="!icon ? faPlay : icon" fixed-width />
        <span v-if="title" class="ml-1">{{ title }}</span>
    </BButton>
</template>
