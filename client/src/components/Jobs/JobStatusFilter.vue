<script setup lang="ts">
import { faCheckCircle, faExclamationTriangle, faSpinner, faStopCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import type { STATE_GROUPS } from "@/components/Jobs/JobsFilters";

import GButton from "../BaseComponents/GButton.vue";
import GButtonGroup from "../BaseComponents/GButtonGroup.vue";

/** One quick-toggle button per `STATE_GROUPS` key, in display order. */
const GROUPS = [
    { key: "active", label: "Active", icon: faSpinner, color: "yellow" },
    { key: "finished", label: "Finished", icon: faCheckCircle, color: "green" },
    { key: "problem", label: "Problem", icon: faExclamationTriangle, color: "red" },
    { key: "inactive", label: "Inactive", icon: faStopCircle, color: "grey" },
] as const satisfies { key: keyof typeof STATE_GROUPS; label: string; icon: unknown; color: string }[];

const props = defineProps<{
    /** The currently active `status` value, or `undefined` if none is toggled on. */
    activeGroup?: string;
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
    <GButtonGroup class="job-state-filter" size="small">
        <GButton
            v-for="group in GROUPS"
            :key="group.key"
            :color="group.color"
            outline
            icon-only
            :pressed="activeGroup === group.key"
            :title="`${activeGroup === group.key ? 'Clear' : 'Show only'} ${group.label.toLowerCase()} jobs`"
            tooltip
            @click="toggle(group.key)">
            <FontAwesomeIcon :icon="group.icon" />
        </GButton>
    </GButtonGroup>
</template>

<style scoped lang="scss">
.job-state-filter {
    width: 100%;
    display: flex;
    justify-content: space-between;

    .g-button {
        width: 100%;
        justify-content: center;
    }
}
</style>
