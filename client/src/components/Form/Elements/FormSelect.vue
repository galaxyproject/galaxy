<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { computed, onMounted, watch } from "vue";
import Multiselect from "vue-multiselect";

import { useMultiselect } from "@/composables/useMultiselect";
import { uid } from "@/utils/utils";

const { ariaExpanded, onOpen, onClose } = useMultiselect();

type SelectValue = Record<string, unknown> | string | number | boolean;

interface SelectOption {
    label: string;
    value: SelectValue;
}

interface Props {
    options: SelectOption[];
    id?: string;
    disabled?: boolean;
    multiple?: boolean;
    optional?: boolean;
    placeholder?: string;
    value?: SelectValue | SelectValue[];
}

const props = withDefaults(defineProps<Props>(), {
    id: `form-select-${uid()}`,
    disabled: false,
    multiple: false,
    optional: false,
    placeholder: "Select Value",
    value: undefined,
});

const emit = defineEmits<{
    (e: "input", value?: SelectValue | SelectValue[]): void;
}>();

/**
 * When there are more options than this, push selected options to the end
 */
const optionReorderThreshold = 8;

const reorderedOptions = computed(() => {
    if (props.options.length <= optionReorderThreshold) {
        return props.options;
    } else {
        const selectedOptions: SelectOption[] = [];
        const unselectedOptions: SelectOption[] = [];

        props.options.forEach((option) => {
            if (selectedValues.value.includes(option.value)) {
                selectedOptions.push(option);
            } else {
                unselectedOptions.push(option);
            }
        });

        return [...unselectedOptions, ...selectedOptions];
    }
});

/**
 * Configure deselect label
 */
const deselectLabel = computed(() => {
    return props.multiple ? "Click to remove" : "";
});

/**
 * Tracks if the select field has options
 */
const hasOptions = computed(() => {
    return props.options.length > 0;
});

/**
 * Provides initial value if necessary
 */
const initialValue = computed(() => {
    if (props.value === undefined && !props.optional && hasOptions.value) {
        const v = props.options[0];

        if (v) {
            return v.value;
        }
    }

    return undefined;
});

/**
 * Configure selected label
 */
const selectedLabel = computed(() => {
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
    set: (val: SelectOption | SelectOption[]) => {
        if (Array.isArray(val)) {
            if (val.length > 0) {
                const values: Array<SelectValue> = val.map((v: SelectOption) => v.value);
                emit("input", values);
            } else {
                emit("input", undefined);
            }
        } else {
            emit("input", val ? val.value : undefined);
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
    <div>
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
            :options="reorderedOptions"
            :placeholder="placeholder"
            :selected-label="selectedLabel"
            select-label="Click to select"
            track-by="value"
            @open="onOpen"
            @close="onClose" />
        <slot v-else name="no-options">
            <BAlert v-localize class="w-100" variant="warning" show> No options available. </BAlert>
        </slot>
    </div>
</template>
