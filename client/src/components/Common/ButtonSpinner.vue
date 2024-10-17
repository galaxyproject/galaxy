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
    variant?: string;
    icon?: IconDefinition;
}

withDefaults(defineProps<Props>(), {
    title: "",
    wait: false,
    tooltip: "",
    disabled: false,
    variant: "primary",
    icon: undefined,
});
</script>

<template>
    <BButton
        v-if="wait"
        v-b-tooltip.hover.bottom
        disabled
        variant="info"
        title="Please Wait..."
        class="d-flex flex-nowrap align-items-center text-nowrap">
        <FontAwesomeIcon :icon="faSpinner" fixed-width spin />
        <slot>
            <span v-if="title">{{ title }}</span>
        </slot>
    </BButton>
    <BButton
        v-else
        v-b-tooltip.hover.bottom
        :variant="variant"
        class="d-flex flex-nowrap align-items-center text-nowrap"
        :title="tooltip"
        :disabled="disabled"
        @click="$emit('onClick')">
        <FontAwesomeIcon :icon="!icon ? faPlay : icon" fixed-width />
        <slot>
            <span v-if="title">{{ title }}</span>
        </slot>
    </BButton>
</template>
