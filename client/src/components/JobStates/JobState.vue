<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import type { JobBaseModel } from "@/api/jobs";
import { getHeaderClass, iconClasses } from "@/composables/useInvocationGraph";

const props = defineProps<{
    job: JobBaseModel;
}>();

const badgeClass = computed(() => {
    return {
        ...getHeaderClass(props.job.state),
        "text-center": true,
    };
});

const stateIcon = computed(() => iconClasses[props.job.state] || null);
</script>

<template>
    <span class="rounded px-2 py-1" :class="badgeClass">
        <FontAwesomeIcon v-if="stateIcon" :icon="stateIcon.icon" :spin="stateIcon.spin" />
        {{ props.job.state }}
    </span>
</template>
