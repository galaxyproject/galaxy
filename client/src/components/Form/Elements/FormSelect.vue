<script setup lang="ts">
import { computed, type ComputedRef, onMounted, watch } from "vue";
import Multiselect from "vue-multiselect";

import { useMultiselect } from "@/composables/useMultiselect";
import { uid } from "@/utils/utils";

const { ariaExpanded, onOpen, onClose } = useMultiselect();

type SelectValue = Record<string, unknown> | string | number | null;

interface SelectOption {
    label: string;
    value: SelectValue;
}

const props = withDefaults(
    defineProps<{
        id?: string;
        disabled?: boolean;
        multiple?: boolean;
        optional?: boolean;
        options: Array<SelectOption>;
        placeholder?: string;
        value?: Array<SelectValue> | Record<string, unknown> | string | number;
    }>(),
    {
        id: `form-select-${uid()}`,
        disabled: false,
        multiple: false,
        optional: false,
        placeholder: "Select value",
        value: null,
    }
);

const emit = defineEmits<{
    (e: "input", value: SelectValue | Array<SelectValue>): void;
}>();

/**
 * Configure deselect label
 */
const deselectLabel: ComputedRef<string> = computed(() => {
    return props.multiple ? "Click to remove" : "";
});

/**
 * Tracks if the select field has options
 */
const hasOptions: ComputedRef<Boolean> = computed(() => {
    return props.options.length > 0;
});

/**
 * Provides initial value if necessary
 */
const initialValue: ComputedRef<SelectValue> = computed(() => {
    if (props.value === null && !props.optional && hasOptions.value) {
        const v = props.options[0];
        if (v) {
            return v.value;
        }
    }
    return null;
});

/**
 * Configure selected label
 */
const selectedLabel: ComputedRef<string> = computed(() => {
    return props.multiple ? "Selected" : "";
});

/**
 * Tracks selected values
 */
const selectedValues = computed(() => (Array.isArray(props.value) ? props.value : [props.value]));

/**
 * Tracks current value and emits changes
 */
const currentValue = computed({
    get: () => props.options.filter((option: SelectOption) => selectedValues.value.includes(option.value)),
    set: (val: Array<SelectOption> | SelectOption): void => {
        if (Array.isArray(val)) {
            if (val.length > 0) {
                const values: Array<SelectValue> = val.map((v: SelectOption) => v.value);
                emit("input", values);
            } else {
                emit("input", null);
            }
        } else {
            emit("input", val ? val.value : null);
        }
    },
});

/**
 * Ensures that an initial value is selected for non-optional inputs
 */
function setInitialValue(): void {
    if (initialValue.value) {
        emit("input", initialValue.value);
    }
}

/**
 * Watches changes in select options and adjusts initial value if necessary
 */
watch(
    () => props.options,
    () => setInitialValue()
);

/**
 * Sets initial value if necessary
 */
onMounted(() => {
    setInitialValue();
});
</script>

<template>
    <Multiselect
        v-if="hasOptions"
        :id="id"
        v-model="currentValue"
        :allow-empty="optional"
        :aria-expanded="ariaExpanded"
        :close-on-select="!multiple"
        :disabled="disabled"
        :deselect-label="deselectLabel"
        label="label"
        :multiple="multiple"
        :options="props.options"
        :placeholder="placeholder"
        :selected-label="selectedLabel"
        select-label="Click to select"
        track-by="value"
        @open="onOpen"
        @close="onClose" />
    <b-alert v-else v-localize class="w-100" variant="warning" show> No options available. </b-alert>
</template>
