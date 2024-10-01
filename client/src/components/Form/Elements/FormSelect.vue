<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheckSquare, faSquare } from "@fortawesome/free-regular-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, type ComputedRef, onMounted, type PropType, ref, watch } from "vue";
import Multiselect from "vue-multiselect";

import { useMultiselect } from "@/composables/useMultiselect";
import { uid } from "@/utils/utils";

import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";

library.add(faCheckSquare, faSquare);

const { ariaExpanded, onOpen, onClose } = useMultiselect();

type SelectValue = Record<string, unknown> | string | number | null;
type ValueWithTags = SelectValue & { tags: string[] };

interface SelectOption {
    label: string;
    value: SelectValue;
}

const props = defineProps({
    id: { type: String, default: `form-select-${uid()}` },
    disabled: {
        type: Boolean,
        default: false,
    },
    multiple: {
        type: Boolean,
        default: false,
    },
    optional: {
        type: Boolean,
        default: false,
    },
    options: {
        type: Array as PropType<Array<SelectOption>>,
        required: true,
    },
    placeholder: {
        type: String,
        default: "Select Value",
    },
    value: {
        type: [String, Array] as PropType<SelectValue | SelectValue[]>,
        default: null,
    },
});

const emit = defineEmits<{
    (e: "input", value: SelectValue | Array<SelectValue>): void;
}>();

const filteredOptions = ref<SelectOption[]>(props.options);

/**
 * When there are more options than this, push selected options to the end
 */
const optionReorderThreshold = 8;

const reorderedOptions = computed(() => {
    if (filteredOptions.value.length <= optionReorderThreshold) {
        return filteredOptions.value;
    } else {
        const selectedOptions: SelectOption[] = [];
        const unselectedOptions: SelectOption[] = [];

        filteredOptions.value.forEach((option) => {
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
 * Tracks if the select field has options
 */
const hasOptions: ComputedRef<Boolean> = computed(() => {
    return filteredOptions.value.length > 0;
});

/**
 * Provides initial value if necessary
 */
const initialValue: ComputedRef<SelectValue> = computed(() => {
    if (props.value === null && !props.optional && hasOptions.value) {
        const v = filteredOptions.value[0];
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
    get: () => filteredOptions.value.filter((option: SelectOption) => selectedValues.value.includes(option.value)),
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
    filteredOptions.value = props.options;
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

function isValueWithTags(item: SelectValue): item is ValueWithTags {
    return item !== null && typeof item === "object" && (item as ValueWithTags).tags !== undefined;
}

function onSearchChange(search: string): void {
    filteredOptions.value = search
        ? props.options.filter((option) => filterByLabelOrTags(option, search))
        : props.options;
}

function filterByLabelOrTags(option: SelectOption, search: string): boolean {
    return (
        option.label.toLowerCase().includes(search.toLowerCase()) ||
        (isValueWithTags(option.value) &&
            option.value.tags.some((tag) => tag.toLowerCase().includes(search.toLowerCase())))
    );
}
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
            :deselect-label="null"
            label="label"
            :multiple="multiple"
            :options="reorderedOptions"
            :placeholder="placeholder"
            :selected-label="selectedLabel"
            :select-label="null"
            track-by="value"
            :internal-search="false"
            @search-change="onSearchChange"
            @open="onOpen"
            @close="onClose">
            <template v-slot:option="{ option }">
                <div class="d-flex align-items-center justify-content-between">
                    <div>
                        <span>{{ option.label }}</span>
                        <StatelessTags
                            v-if="isValueWithTags(option.value)"
                            class="tags mt-2"
                            :value="option.value.tags"
                            disabled />
                    </div>
                    <FontAwesomeIcon v-if="selectedValues.includes(option.value)" :icon="faCheckSquare" />
                    <FontAwesomeIcon v-else :icon="faSquare" />
                </div>
            </template>
        </Multiselect>
        <slot v-else name="no-options">
            <b-alert v-localize class="w-100" variant="warning" show> No options available. </b-alert>
        </slot>
    </div>
</template>
