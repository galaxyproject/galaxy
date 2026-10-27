<script setup lang="ts">
import type { SelectOption } from "@galaxyproject/galaxy-ui";
import { computed } from "vue";

import type { JobTimeRangeKey } from "@/components/Jobs/JobsFilters";

import GSelect from "@/components/BaseComponents/GSelect.vue";

/** Quick-pick time ranges; each maps to a `update_time_gt` cutoff computed from "now". */
const RANGE_OPTIONS: SelectOption<JobTimeRangeKey | undefined>[] = [
    { value: undefined, text: "Anytime" },
    { value: "30m", text: "Last 30 mins" },
    { value: "1h", text: "Last hour" },
    { value: "24h", text: "Last 24 hours" },
    { value: "7d", text: "Last week" },
];

/** Shown, selected and disabled only while `activeRange` is "custom" if a user-entered
 * `update_time` filter that doesn't match any quick-pick range above. */
const CUSTOM_RANGE_OPTION: SelectOption<"custom"> = { value: "custom", text: "Custom range", disabled: true };

const props = defineProps<{
    /**
     * The currently active range key, "custom" for a user-entered `update_time` filter, or
     * `undefined` for "Anytime".
     * @default undefined
     */
    activeRange?: JobTimeRangeKey | undefined;
}>();

const emit = defineEmits<{
    /** Emitted with the chosen range key, or `undefined` for "Anytime". Never emitted for "custom",
     * since that option is disabled. */
    (e: "update:active-range", range: JobTimeRangeKey | undefined): void;
}>();

const options = computed(() =>
    props.activeRange === "custom" ? [CUSTOM_RANGE_OPTION, ...RANGE_OPTIONS] : RANGE_OPTIONS,
);
</script>

<template>
    <div>
        <GSelect
            size="small"
            :model-value="props.activeRange"
            :options="options"
            aria-label="Filter jobs by time range"
            @update:model-value="(value) => emit('update:active-range', value || undefined)" />
    </div>
</template>
