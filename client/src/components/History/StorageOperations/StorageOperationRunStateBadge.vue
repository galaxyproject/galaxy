<script setup lang="ts">
import { faCheckCircle, faClock, faExclamationCircle, faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import localize from "@/utils/localization";

interface Props {
    state: string;
    failedCount?: number;
    skippedCount?: number;
}

const props = withDefaults(defineProps<Props>(), {
    failedCount: 0,
    skippedCount: 0,
});

const statusLabel = computed(() => {
    if (props.state === "completed") {
        if ((props.failedCount ?? 0) > 0) {
            return localize("Completed with failures");
        }
        if ((props.skippedCount ?? 0) > 0) {
            return localize("Completed with skips");
        }
        return localize("Completed successfully");
    }
    if (props.state === "running") {
        return localize("Running");
    }
    if (props.state === "failed") {
        return localize("Failed");
    }
    return props.state;
});

const statusIcon = computed(() => {
    if (props.state === "completed") {
        if ((props.failedCount ?? 0) > 0) {
            return faExclamationCircle;
        }
        if ((props.skippedCount ?? 0) > 0) {
            return faExclamationTriangle;
        }
        return faCheckCircle;
    }
    if (props.state === "failed") {
        return faExclamationCircle;
    }
    return faClock;
});

const iconClass = computed(() => {
    if (props.state === "failed") {
        return "text-danger";
    }
    if (props.state === "completed") {
        if ((props.failedCount ?? 0) > 0) {
            return "text-danger";
        }
        if ((props.skippedCount ?? 0) > 0) {
            return "text-warning";
        }
        return "text-success";
    }
    if (props.state === "running") {
        return "text-info";
    }
    return "text-secondary";
});
</script>

<template>
    <div v-g-tooltip.hover class="storage-run-state-badge" :title="statusLabel">
        <FontAwesomeIcon :icon="statusIcon" fixed-width :class="iconClass" />
    </div>
</template>

<style scoped>
.storage-run-state-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
}
</style>
