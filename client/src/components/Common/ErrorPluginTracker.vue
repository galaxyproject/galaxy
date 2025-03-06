<script setup lang="ts">
import { computed } from "vue";

import { getGalaxyInstance } from "@/app";

const errorReportingAvailable = computed(() => {
    const Galaxy = getGalaxyInstance();
    return Galaxy.Sentry.isInitialized ?? "Your error has been logged in Sentry to improve your experience.";
});
</script>
<template>
    <span v-localize>
        {{ errorReportingAvailable }}
    </span>
</template>
