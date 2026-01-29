<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import type { JobState } from "@/api/jobs";
import { iconClasses, statePlaceholders } from "@/composables/useInvocationGraph";

const props = defineProps<{
    state: JobState;
    jobCount: number;
}>();
</script>

<template>
    <span class="d-flex align-items-center">
        <FontAwesomeIcon
            v-if="iconClasses[props.state]"
            :icon="iconClasses[props.state]?.icon"
            :class="iconClasses[props.state]?.class"
            :spin="iconClasses[props.state]?.spin"
            size="sm"
            class="mr-1" />
        {{ props.jobCount }} job{{ props.jobCount > 1 ? "s" : "" }} {{ statePlaceholders[props.state] || props.state }}
    </span>
</template>
