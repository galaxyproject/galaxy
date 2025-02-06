<script setup lang="ts">
import { getGalaxyInstance } from "@/app";
import { computed } from "vue";

const errorReportingAvailable = computed(() =>{
    const Galaxy = getGalaxyInstance();
    if (!!Galaxy.Sentry.isInitialized) {
        return "Your error has been logged in Sentry to improve your experience.";
    }
});
</script>
<template>
    <span v-localize>
        {{ errorReportingAvailable }}
    </span>
</template>
