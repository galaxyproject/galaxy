<script setup lang="ts">
import { formatDistanceToNow, parseISO } from "date-fns";
import { formatInTimeZone } from "date-fns-tz";
import { computed } from "vue";

const props = defineProps({
    date: { type: String, required: true },
    mode: {
        type: String,
        default: "date",
    },
});

// Component assumes ISO format date, but note that in Galaxy this won't have
// TZinfo -- it will always be Zulu
const parsedDate = computed(() => {
    return parseISO(`${props.date}Z`);
});

const elapsedTime = computed(() => {
    return formatDistanceToNow(parsedDate.value, { addSuffix: true });
});

const fullISO = computed(() => {
    return parsedDate.value.toISOString();
});

const pretty = computed(() => {
    return `${formatInTimeZone(parsedDate.value, "Etc/Zulu", "eeee MMM do H:mm:ss yyyy")} UTC`;
});
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
