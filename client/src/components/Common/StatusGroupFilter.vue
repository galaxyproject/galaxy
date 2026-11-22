<script setup lang="ts">
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import type { ComponentColor } from "@/components/BaseComponents/componentVariants";

import GButton from "@/components/BaseComponents/GButton.vue";
import GButtonGroup from "@/components/BaseComponents/GButtonGroup.vue";

/** One quick-toggle button, standing for a group of states. */
export interface StatusGroup {
    key: string;
    label: string;
    icon: IconDefinition;
    color: ComponentColor;
}

const props = defineProps<{
    /** One quick-toggle button per group key, in display order. */
    groups: readonly StatusGroup[];
    /** The listed items in the plural, for the buttons' titles (e.g. "invocations"). */
    noun: string;
    /** The currently active `status` value, or `undefined` if none is toggled on. */
    activeGroup?: string;
    /** Show each group's label next to its icon. */
    showLabels?: boolean;
}>();

const emit = defineEmits<{
    /** Emitted with the clicked group's key, or `undefined` if the already-active group was clicked again. */
    (e: "update:active-group", group: string | undefined): void;
}>();

function toggle(key: string) {
    emit("update:active-group", props.activeGroup === key ? undefined : key);
}
</script>

<template>
    <GButtonGroup class="status-group-filter" size="small" :aria-label="`Filter ${noun} by status`">
        <GButton
            v-for="group in groups"
            :key="group.key"
            :color="group.color"
            outline
            :icon-only="!showLabels"
            :pressed="activeGroup === group.key"
            :title="`${activeGroup === group.key ? 'Clear' : 'Show only'} ${group.label.toLowerCase()} ${noun}`"
            :tooltip="!showLabels"
            :data-status-group="group.key"
            @click="toggle(group.key)">
            <FontAwesomeIcon :icon="group.icon" />
            <span v-if="showLabels">{{ group.label }}</span>
        </GButton>
    </GButtonGroup>
</template>

<style scoped lang="scss">
.status-group-filter {
    width: 100%;
    display: flex;
    justify-content: space-between;

    .g-button {
        width: 100%;
        justify-content: center;
    }
}
</style>
