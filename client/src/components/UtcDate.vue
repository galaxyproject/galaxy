<script setup lang="ts">
import { formatDistanceToNow } from "date-fns";
import { computed } from "vue";

import { galaxyTimeToDate, localizeUTCPretty } from "@/utils/dates";

interface UtcDateProps {
    date: string;
    mode?: "date" | "elapsed" | "pretty";
}

const props = withDefaults(defineProps<UtcDateProps>(), {
    mode: "date",
});

const parsedDate = computed(() => galaxyTimeToDate(props.date));
const elapsedTime = computed(() => formatDistanceToNow(parsedDate.value, { addSuffix: true }));
const fullISO = computed(() => parsedDate.value.toISOString());
const pretty = computed(() => localizeUTCPretty(parsedDate.value));
</script>

<template>
    <span v-if="mode == 'date'" class="utc-time" :title="elapsedTime">
        {{ fullISO }}
    </span>
    <span v-else-if="mode === 'elapsed'" class="utc-time utc-time-elapsed" :title="fullISO">
        {{ elapsedTime }}
    </span>
    <span v-else class="utc-time" :title="elapsedTime">
        {{ pretty }}
    </span>
</template>
