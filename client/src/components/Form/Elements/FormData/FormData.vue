<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCopy, faFile, faFolder } from "@fortawesome/free-regular-svg-icons";
import { faExclamation, faLink, faUnlink } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BButtonGroup, BFormCheckbox } from "bootstrap-vue";
import { computed, onMounted, type Ref, ref, watch } from "vue";

import { getGalaxyInstance } from "@/app";
import { type EventData, useEventStore } from "@/stores/eventStore";

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
        loading?: boolean;
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
        loading: false,
        multiple: false,
        optional: false,
        value: null,
        extensions: () => [],
        type: "data",
        flavor: null,
        tag: null,
    }
);

const eventStore = useEventStore();

const $emit = defineEmits(["input"]);

// Determines wether values should be processed as linked or unlinked
const currentLinked = ref(true);

// Indicates which of the select field from the set of variants is currently shown
const currentField = ref(0);

// Field highlighting status
const currentHighlighting: Ref<string | null> = ref(null);

// Drag/Drop related values
const dragData: Ref<EventData | null> = ref(null);
const dragTarget: Ref<EventTarget | null> = ref(null);

/** Store options which need to be preserved **/
const keepOptions: Record<string, SelectOption> = {};

/**
 * Determine whether the file dialog can be used or not
 */
const canBrowse = computed(() => variant.value && !!variant.value.find((v) => v.src === SOURCE.DATASET));

/**
 * Provides the currently shown source type
 */
const currentSource = computed(() => (currentVariant.value ? currentVariant.value.src : null));

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
        if (!props.optional && formattedOptions.value.length > 0) {
            const firstEntry = formattedOptions.value && formattedOptions.value[0];
            if (firstEntry && firstEntry.value) {
                value.push(firstEntry.value);
                return value;
            }
        }
        return null;
    },
    set: (val) => {
        $emit("input", createValue(val));
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
    if (currentSource.value && currentSource.value in props.options) {
        // Map incoming values to available options
        const options = props.options[currentSource.value] || [];
        const result: Array<SelectOption> = [];
        options.forEach((option) => {
            const newOption = {
                label: `${option.hid}: ${option.name}`,
                value: option || null,
            };
            if (option.keep) {
                const keepKey = `${option.id}_${option.src}`;
                keepOptions[keepKey] = newOption;
            } else {
                const accepted = !props.tag || option.tags?.includes(props.tag);
                if (accepted) {
                    result.push(newOption);
                }
            }
        });
        // Add keep-options from other sources
        const otherSources = [SOURCE.COLLECTION_ELEMENT, SOURCE.LIBRARY_DATASET];
        for (const otherSource of otherSources) {
            const otherOptions = props.options[otherSource];
            if (Array.isArray(otherOptions)) {
                otherOptions.forEach((option) => {
                    const keepKey = `${option.id}_${option.src}`;
                    const sourceLabel = getSourceLabel(getSourceType(option));
                    const newOption = {
                        label: `${option.name} (as ${sourceLabel})`,
                        value: option || null,
                    };
                    keepOptions[keepKey] = newOption;
                });
            }
        }
        // Populate keep-options from cache
        Object.entries(keepOptions).forEach(([key, option]) => {
            if (option.value && getSourceType(option.value) === currentSource.value) {
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
        // Add optional entry
        if (!currentVariant.value?.multiple && props.optional) {
            result.unshift({
                label: "Nothing selected",
                value: null,
            });
        }
        return result;
    } else {
        return [];
    }
});

/**
 * Provides placeholder label for select field
 */
const placeholder = computed(() => getSourceLabel(currentSource.value));

/**
 * Provides the array of available variants associated with a specific form data type
 */
const variant = computed(() => {
    const flavorKey = props.flavor ? `${props.flavor}_` : "";
    const multipleKey = props.multiple ? `_multiple` : "";
    const variantKey = `${flavorKey}${props.type}${multipleKey}`;
    return VARIANTS[variantKey];
});

/**
 * Clears highlighting with delay
 */
function clearHighlighting(timeout = 1000) {
    setTimeout(() => {
        currentHighlighting.value = null;
    }, timeout);
}

/**
 * Create final input element value
 */
function createValue(val: Array<DataOption> | DataOption | null) {
    if (val) {
        const values = Array.isArray(val) ? val : [val];
        if (variant.value && values.length > 0 && values[0]) {
            const hasMapOverType = values.find((v) => !!v.map_over_type);
            const isMultiple = values.length > 1;

            // Determine source representation (uses only the initial value)
            const sourceType = getSourceType(values[0]);

            // Identify matching variant
            const variantIndex = variant.value.findIndex(
                (v) => (!isMultiple || v.multiple === isMultiple) && v.src === sourceType
            );

            // Determine batch mode
            let batch: string = BATCH.DISABLED;
            if (variantIndex >= 0) {
                const variantDetails = variant.value[variantIndex];
                if (variantDetails) {
                    // Switch to another field type if source differs from current field
                    if (isMultiple || (currentVariant.value && currentVariant.value.src !== sourceType)) {
                        currentField.value = variantIndex;
                        batch = variantDetails.batch;
                    } else {
                        batch = (currentVariant.value && currentVariant.value.batch) || BATCH.DISABLED;
                    }
                }
            }
            // Emit new value
            return {
                batch: batch !== BATCH.DISABLED || !!hasMapOverType,
                product: batch === BATCH.ENABLED && !currentLinked.value,
                values: values.map((entry) => ({
                    id: entry.id,
                    src: entry.src,
                    map_over_type: entry.map_over_type || null,
                })),
            };
        }
    } else {
        return null;
    }
}

/**
 * Return user-friendly data source label
 */
function getSourceLabel(src: string | null) {
    return src === SOURCE.DATASET ? "dataset" : "dataset collection";
}

/**
 * Determine source type of a given value
 */
function getSourceType(val: DataOption) {
    if (val.src === SOURCE.COLLECTION_ELEMENT) {
        return val.is_dataset ? SOURCE.DATASET : SOURCE.COLLECTION;
    } else if (val.src === SOURCE.LIBRARY_DATASET) {
        return SOURCE.DATASET;
    } else {
        return val.src;
    }
}

/** Add values from drag/drop or data dialog sources */
function handleIncoming(incoming: Record<string, unknown>, partial = true) {
    if (incoming) {
        const values = Array.isArray(incoming) ? incoming : [incoming];
        if (values.length > 0) {
            const incomingValues: Array<DataOption> = [];
            values.forEach((v) => {
                // Map incoming objects to data option values
                const newHid = v.hid;
                const newId = v.id;
                const newName = v.name ? v.name : newId;
                const newSrc =
                    v.src || (v.history_content_type === "dataset_collection" ? SOURCE.COLLECTION : SOURCE.DATASET);
                const newValue = {
                    id: newId,
                    src: newSrc,
                    hid: newHid,
                    name: newName,
                    keep: true,
                    tags: [],
                };
                // Verify that new value has corresponding option
                const keepKey = `${newId}_${newSrc}`;
                const existingOptions = props.options && props.options[newSrc];
                const foundOption = existingOptions && existingOptions.find((option) => option.id === newId);
                if (!foundOption && !(keepKey in keepOptions)) {
                    keepOptions[keepKey] = { label: `${newHid || "Selected"}: ${newName}`, value: newValue };
                }
                // Add new value to list
                incomingValues.push(newValue);
            });
            if (incomingValues.length > 0 && incomingValues[0]) {
                // Set new value
                const config = currentVariant.value;
                const firstValue = incomingValues[0];
                if (config && config.src == firstValue.src && partial) {
                    if (config.multiple) {
                        const newValues = currentValue.value ? currentValue.value.slice() : [];
                        incomingValues.forEach((v) => {
                            newValues.push(v);
                        });
                        currentValue.value = newValues;
                    } else {
                        currentValue.value = [firstValue];
                    }
                } else {
                    currentValue.value = incomingValues;
                }
            }
        }
    }
}

/**
 * Open file dialog
 */
function onBrowse() {
    if (currentVariant.value) {
        const library = !!currentVariant.value.library;
        const multiple = !!currentVariant.value.multiple;
        getGalaxyInstance().data.dialog(
            (response: Record<string, unknown>) => {
                handleIncoming(response, false);
            },
            {
                allowUpload: true,
                format: null,
                library,
                multiple,
            }
        );
    }
}

/**
 * Drag/Drop event handlers
 */
function onDragEnter(evt: MouseEvent) {
    const eventData = eventStore.getDragData();
    if (eventData) {
        dragTarget.value = evt.target;
        dragData.value = eventData;
    }
}

function onDragLeave(evt: MouseEvent) {
    if (dragTarget.value === evt.target) {
        currentHighlighting.value = null;
    }
}

function onDragOver() {
    if (dragData.value !== null) {
        currentHighlighting.value = "warning";
    }
}

function onDrop() {
    if (dragData.value) {
        handleIncoming(dragData.value);
        currentHighlighting.value = "success";
        dragData.value = null;
        clearHighlighting();
    }
}

/**
 * Matches an array of values to available options
 */
const matchedValues = computed(() => {
    const values: Array<DataOption> = [];
    if (props.value && props.value.values.length > 0) {
        props.value.values.forEach((entry) => {
            if ("src" in entry && entry.src) {
                const options = props.options[entry.src] || [];
                const option = options.find((v) => v.id === entry.id && v.src === entry.src);
                if (option) {
                    values.push({ ...option, name: option.name || entry.id });
                }
            }
        });
    }
    return values;
});

onMounted(() => {
    if (props.value) {
        $emit("input", createValue(matchedValues.value));
    } else {
        $emit("input", createValue(currentValue.value));
    }
});

/**
 * Watch and set current value if user switches to a different select field
 */
watch(
    () => [props.options, currentLinked.value, currentVariant.value],
    () => {
        $emit("input", createValue(currentValue.value));
    }
);
</script>

<template>
    <div
        :class="currentHighlighting && `ui-dragover-${currentHighlighting}`"
        @dragenter.prevent="onDragEnter"
        @dragleave.prevent="onDragLeave"
        @dragover.prevent="onDragOver"
        @drop.prevent="onDrop">
        <div>
            <div class="d-flex">
                <BButtonGroup v-if="variant.length > 1" buttons class="align-self-start mr-2">
                    <BButton
                        v-for="(v, index) in variant"
                        :key="index"
                        v-b-tooltip.hover.bottom
                        :pressed="currentField === index"
                        :title="v.tooltip"
                        @click="currentField = index">
                        <FontAwesomeIcon :icon="['far', v.icon]" />
                    </BButton>
                    <BButton
                        v-if="canBrowse"
                        v-b-tooltip.hover.bottom
                        title="Browse or Upload Datasets"
                        @click="onBrowse">
                        <FontAwesomeIcon v-if="loading" icon="fa-spinner" spin />
                        <span v-else class="font-weight-bold">...</span>
                    </BButton>
                </BButtonGroup>
                <FormSelect
                    v-if="currentVariant"
                    v-model="currentValue"
                    :multiple="currentVariant.multiple"
                    :optional="optional"
                    :options="formattedOptions"
                    :placeholder="`Select a ${placeholder}`" />
            </div>
            <div v-if="currentVariant.batch !== BATCH.DISABLED">
                <BFormCheckbox
                    v-if="currentVariant.batch === BATCH.ENABLED"
                    v-model="currentLinked"
                    class="no-highlight my-2"
                    switch>
                    <span v-if="currentLinked">
                        <FontAwesomeIcon icon="fa-link" />
                        <b v-localize class="mr-1">Linked:</b>
                        <span v-localize>Datasets will be run in matched order with other datasets.</span>
                    </span>
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
    </div>
</template>
