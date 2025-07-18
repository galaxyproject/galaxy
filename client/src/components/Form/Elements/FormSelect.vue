<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheckSquare, faSquare } from "@fortawesome/free-regular-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, type ComputedRef, onMounted, type PropType, ref, watch } from "vue";
import Multiselect from "vue-multiselect";

import { useFilterObjectArray } from "@/composables/filter";
import { useMultiselect } from "@/composables/useMultiselect";
import { uid } from "@/utils/utils";

import { type DataOption, isDataOption, itemUniqueKey } from "./FormData/types";

import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";

library.add(faCheckSquare, faSquare);

const { ariaExpanded, onOpen, onClose } = useMultiselect();

type SelectValue = Record<string, unknown> | string | number | null;
type ValueWithTags = SelectValue & { tags: string[] };

interface SelectOption {
    label: string;
    value: SelectValue;
    key?: string;
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

const filter = ref("");
const filteredOptions = useFilterObjectArray(() => props.options, filter, ["label", ["value", "tags"]]);

/**
 * When there are more options than this, push selected options to the end
 */
const optionReorderThreshold = 8;

const reorderedOptions = computed(() => {
    let result;
    if (!props.multiple || filteredOptions.value.length <= optionReorderThreshold) {
        result = filteredOptions.value;
    } else {
        const selectedOptions: SelectOption[] = [];
        const unselectedOptions: SelectOption[] = [];

        filteredOptions.value.forEach((option) => {
            if (isSelected(option.value)) {
                selectedOptions.push(option);
            } else {
                unselectedOptions.push(option);
            }
        });

        result = [...unselectedOptions, ...selectedOptions];
    }
    return result.map(getSelectOption);
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
 * Tracks selected keys in case of form data options
 */
const selectedKeys = computed(() => {
    return selectedValues.value
        .map((v) => (isDataOptionObject(v) ? itemUniqueKey(v) : undefined))
        .filter((v) => v !== undefined);
});

/**
 * Whether current value(s) will be tracked by key or value
 */
const trackBy = computed(() => {
    return selectedKeys.value.length > 0 ? "key" : "value";
});

/**
 * Tracks current value and emits changes
 */
const currentValue = computed({
    get: () => {
        // Preserve the order of props.value
        const values = Array.isArray(props.value) ? props.value : [props.value];
        return values
            .map((val) => {
                // Find the matching option in props.options
                const option = props.options.find(
                    (opt) =>
                        isSelected(opt.value) &&
                        (isDataOptionObject(val)
                            ? isDataOptionObject(opt.value) && itemUniqueKey(opt.value) === itemUniqueKey(val)
                            : opt.value === val)
                );
                return option ? getSelectOption(option) : undefined;
            })
            .filter((v) => v !== undefined);
    },
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

function getSelectOption(option: SelectOption): SelectOption {
    if (isDataOptionObject(option.value)) {
        return {
            ...option,
            key: itemUniqueKey(option.value),
        };
    }
    return option;
}

/**
 * Watches changes in select options and adjusts initial value if necessary
 */
watch(
    () => props.options,
    () => {
        setInitialValue();
    }
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

function isDataOptionObject(item: SelectValue): item is DataOption {
    return !!item && typeof item === "object" && isDataOption(item);
}

function onSearchChange(search: string): void {
    filter.value = search;
}

function isSelected(item: SelectValue): boolean {
    if (isDataOptionObject(item)) {
        return selectedKeys.value.includes(itemUniqueKey(item));
    }
    return selectedValues.value.includes(item);
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
            :track-by="trackBy"
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
                    <FontAwesomeIcon v-if="isSelected(option.value)" :icon="faCheckSquare" />
                    <FontAwesomeIcon v-else :icon="faSquare" />
                </div>
            </template>
        </Multiselect>
        <slot v-else name="no-options">
            <b-alert v-localize class="w-100" variant="warning" show> No options available. </b-alert>
        </slot>
    </div>
</template>
