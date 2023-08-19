<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCopy, faFile, faFolder } from "@fortawesome/free-regular-svg-icons";
import { faExclamation, faLink, faUnlink } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BFormCheckbox, BFormRadio, BFormRadioGroup } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import type { DataOption } from "./types";
import { BATCH, SOURCE, VARIANTS } from "./variants";

import FormSelect from "@/components/Form/Elements/FormSelect.vue";

library.add(faCopy, faExclamation, faFile, faFolder, faLink, faUnlink);

interface SelectOption {
    label: string;
    value: DataOption | null;
}

const props = withDefaults(
    defineProps<{
        multiple?: boolean;
        optional?: boolean;
        options: Record<string, Array<DataOption>>;
        value?: {
            values: Array<DataOption>;
        };
        extensions?: Array<string>;
        type?: string;
        flavor?: string;
        tag?: string;
    }>(),
    {
        multiple: false,
        optional: false,
        value: null,
        extensions: () => [],
        type: "data",
        flavor: null,
        tag: null,
    }
);

const $emit = defineEmits(["input"]);

// Determines wether values should be processed as linked or unlinked
const currentBatch = ref(true);

// Indicates which of the select field from the set of variants is currently shown
const currentField = ref(0);

/** Store options which need to be preserved **/
const keepOptions: Record<string, SelectOption> = {};

/**
 * Provides the currently shown source type
 */
const currentSource = computed(() => currentVariant.value && currentVariant.value.src);

/**
 * Interface between incoming input value and select field value
 */
const currentValue = computed({
    get: () => {
        const value: Array<DataOption> = [];
        if (props.value) {
            for (const v of props.value.values) {
                const foundEntry = formattedOptions.value.find(
                    (entry) => entry.value && entry.value.id === v.id && entry.value.src === v.src
                );
                if (foundEntry && foundEntry.value) {
                    value.push(foundEntry.value);
                    if (!currentVariant.value?.multiple) {
                        break;
                    }
                }
            }
            if (value.length > 0) {
                return value;
            }
        }
        return null;
    },
    set: (val) => {
        setValue(val);
    },
});

/**
 * Returns the variant i.e. attributes, of the shown select field.
 */
const currentVariant = computed(() => {
    if (variant.value && currentField.value < variant.value.length) {
        return variant.value[currentField.value];
    } else {
        return null;
    }
});

/**
 * Converts and populates options for the shown select field
 */
const formattedOptions = computed(() => {
    const keepSet = new Set();
    if (currentSource.value && currentSource.value in props.options) {
        // Map incoming values to available options
        const options = props.options[currentSource.value] || [];
        const result: Array<SelectOption> = options.map((option) => {
            const newOption = {
                label: `${option.hid}: ${option.name}`,
                value: option || null,
            };
            if (option.keep) {
                const keepKey = `${option.id}_${option.src}`;
                if (!(keepKey in keepOptions)) {
                    keepOptions[keepKey] = newOption;
                    keepSet.add(keepKey);
                }
            }
            return newOption;
        });
        // Populate keep-options from cache
        Object.entries(keepOptions).forEach(([key, option]) => {
            if (!keepSet.has(key) && option.value?.src === currentSource.value) {
                result.unshift(option);
            }
        });
        // Sort entries by hid
        result.sort((a, b) => {
            const aHid = a.value && a.value.hid;
            const bHid = b.value && b.value.hid;
            if (aHid && bHid) {
                return bHid - aHid;
            } else {
                return 0;
            }
        });
        return result;
    } else {
        return [];
    }
});

/**
 * Provides placeholder label for select field
 */
const placeholder = computed(() => (currentSource.value === "hda" ? "dataset" : "dataset collection"));

/**
 * Provides the array of available variants associated with a specific form data type
 */
const variant = computed(() => {
    const flavorKey = props.flavor ? `${props.flavor}_` : "";
    const multipleKey = props.multiple ? `_${props.multiple}` : "";
    const variantKey = `${flavorKey}${props.type}${multipleKey}`;
    return VARIANTS[variantKey];
});

/**
 * Processes and submits values from the select field
 */
function setValue(val: Array<DataOption> | DataOption | null) {
    const batchMode = currentVariant.value && currentVariant.value.batch;
    if (val) {
        const values = Array.isArray(val) ? val : [val];
        $emit("input", {
            batch: batchMode !== BATCH.DISABLED,
            product: batchMode === BATCH.ENABLED && !currentBatch.value,
            values: values.map((entry) => ({
                id: entry.id,
                src: entry.src,
                map_over_type: entry.map_over_type,
            })),
        });
    } else {
        $emit("input", null);
    }
}

/**
 * Watch and set current value if user switches to a different select field
 */
watch(
    () => currentVariant.value,
    () => {
        setValue(currentValue.value);
    }
);
</script>

<template>
    <div>
        <div class="d-flex">
            <BFormRadioGroup v-if="variant.length > 1" v-model="currentField" buttons class="align-self-start mr-2">
                <BFormRadio
                    v-for="(v, index) in variant"
                    v-b-tooltip.hover.bottom
                    :key="index"
                    :title="v.tooltip"
                    :value="index">
                    <FontAwesomeIcon :icon="['far', v.icon]" />
                </BFormRadio>
            </BFormRadioGroup>
            <FormSelect
                v-if="currentVariant"
                v-model="currentValue"
                class="w-100"
                :multiple="currentVariant.multiple"
                :optional="optional"
                :options="formattedOptions"
                :placeholder="`Select a ${placeholder}`" />
        </div>
        <div v-if="currentVariant.batch !== BATCH.DISABLED">
            <BFormCheckbox
                v-if="currentVariant.batch === BATCH.ENABLED"
                v-model="currentBatch"
                class="no-highlight my-2"
                switch>
                <div v-if="currentBatch">
                    <FontAwesomeIcon icon="fa-link" />
                    <b v-localize class="mr-1">Linked:</b>
                    <span v-localize>Datasets will be run in matched order with other datasets.</span>
                </div>
                <span v-else>
                    <FontAwesomeIcon icon="fa-unlink" />
                    <b v-localize class="mr-1">Unlinked:</b>
                    <span v-localize>Dataset will be run against *all* other datasets.</span>
                </span>
            </BFormCheckbox>
            <div class="text-info my-2">
                <FontAwesomeIcon icon="fa-exclamation" />
                <span v-localize class="ml-1">
                    This is a batch mode input field. Individual jobs will be triggered for each dataset.
                </span>
            </div>
        </div>
    </div>
</template>
