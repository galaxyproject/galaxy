<script setup lang="ts">
import { faPlay, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";

interface Props {
    title: string;
    wait?: boolean;
    tooltip?: string;
    disabled?: boolean;
    size?: string;
    variant?: string;
    hasPlayIcon?: boolean;
}

withDefaults(defineProps<Props>(), {
    wait: false,
    tooltip: "",
    disabled: false,
    size: "md",
    variant: "primary",
    hasPlayIcon: true,
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
        <FontAwesomeIcon :icon="faSpinner" class="mr-2" spin />
        <slot>{{ title }}</slot>
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
        <FontAwesomeIcon v-if="hasPlayIcon" :icon="faPlay" class="mr-2" />
        <slot>{{ title }}</slot>
    </BButton>
</template>
