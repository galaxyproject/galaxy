<script setup lang="ts">
import type { SelectOption } from "@galaxyproject/galaxy-ui";
import { computed } from "vue";

import { CUSTOM_TIME_RANGE, type TimeRange } from "@/components/Common/TimeRangeFilter.types";

import GSelect from "@/components/BaseComponents/GSelect.vue";

/** Shown, selected and disabled only while `activeRange` is "custom", for a typed range filter that
 * no quick-pick range matches. */
const CUSTOM_RANGE_OPTION: SelectOption<string> = { value: CUSTOM_TIME_RANGE, text: "Custom range", disabled: true };

const props = defineProps<{
    /** The quick-pick ranges, in display order, after "Anytime". */
    ranges: readonly TimeRange[];
    /** The listed items in the plural, for the select's label (e.g. "invocations"). */
    noun: string;
    /**
     * The currently active range key, "custom" for a user-entered range filter, or
     * `undefined` for "Anytime".
     * @default undefined
     */
    activeRange?: string;
}>();

const emit = defineEmits<{
    /** Emitted with the chosen range key, or `undefined` for "Anytime". Never emitted for "custom",
     * since that option is disabled. */
    (e: "update:active-range", range: string | undefined): void;
}>();

/** "Anytime", then the quick-pick time ranges. */
const rangeOptions = computed<SelectOption<string | undefined>[]>(() => [
    { value: undefined, text: "Anytime" },
    ...props.ranges.map((range) => ({ value: range.key, text: range.label })),
]);

const options = computed(() =>
    props.activeRange === CUSTOM_TIME_RANGE ? [CUSTOM_RANGE_OPTION, ...rangeOptions.value] : rangeOptions.value,
);
</script>

<template>
    <div>
        <GSelect
            size="small"
            :model-value="props.activeRange"
            :options="options"
            :aria-label="`Filter ${props.noun} by time range`"
            @update:model-value="(value) => emit('update:active-range', value || undefined)" />
    </div>
</template>
