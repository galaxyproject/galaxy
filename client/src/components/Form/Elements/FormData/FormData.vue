<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCopy, faFile, faFolder } from "@fortawesome/free-regular-svg-icons";
import { faExclamation, faLink, faUnlink } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BButtonGroup, BFormCheckbox } from "bootstrap-vue";
import Vue, { computed, onMounted, type Ref, ref, watch } from "vue";

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

const eventBus = new Vue();

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
const keepOptions: Ref<Record<string, SelectOption>> = ref({});

/** Displays a wait indicator between setting a value and receiving an update */
const waiting = ref(false);

/**
 * Determine wether the file dialog can be used or not
 */
const canBrowse = computed(() => variant.value && !!variant.value.find((v) => v.src === SOURCE.DATASET));

/**
 * Provides the currently shown source type
 */
const currentSource = computed(() => currentVariant.value && currentVariant.value.src);

/**
 * Interface between incoming input value and select field value
 */
const currentValue = computed({
    get: () => {
        eventBus.$emit("waiting", false);
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
        eventBus.$emit("waiting", true);
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
                keepOptions.value[keepKey] = newOption;
            } else {
                const accepted = !props.tag || option.tags.includes(props.tag);
                if (accepted) {
                    result.push(newOption);
                }
            }
        });
        // Populate keep-options from cache
        Object.entries(keepOptions.value).forEach(([key, option]) => {
            if (option.value?.src === currentSource.value) {
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
 * Dataset collection elements should be treated as plain values.
 */
const isDCE = computed(() => {
    if (props.value) {
        return props.value.values.findIndex((v) => v.src !== SOURCE.COLLECTION_ELEMENT) === -1;
    } else {
        return false;
    }
});

/**
 * Provides placeholder label for select field
 */
const placeholder = computed(() => (currentSource.value === SOURCE.DATASET ? "dataset" : "dataset collection"));

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

/** Add values from drag/drop or data dialog sources */
function handleIncoming(incoming: Record<string, unknown>, partial = true) {
    if (incoming) {
        const values = Array.isArray(incoming) ? incoming : [incoming];
        if (values.length > 0) {
            const incomingValues: Array<DataOption> = [];
            values.forEach((v) => {
                // Map incoming objects to data option values
                v.id = v.element_id || v.id;
                const newHid = v.hid;
                const newId = v.id;
                const newName = v.name ? v.name : newId;
                const newSrc = v.history_content_type === "dataset_collection" ? SOURCE.COLLECTION : SOURCE.DATASET;
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
                if (!foundOption && !(keepKey in keepOptions.value)) {
                    keepOptions.value[keepKey] = { label: `${newHid || "Selected"}: ${newName}`, value: newValue };
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
 * Matches entries to available options
 */
function matchName(entry: DataOption) {
    if ("src" in entry && entry.src) {
        const options = props.options[entry.src] || [];
        const option = options.find((v) => v.id === entry.id && v.src === entry.src);
        if (option) {
            return option.name;
        }
    }
    return entry.id;
}

/**
 * Open file dialog
 */
function onBrowse() {
    if (variant.value) {
        const library = !!variant.value.find((v) => v.library);
        const multiple = !!variant.value.find((v) => v.multiple);
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

/**
 * Insert the dragged item into the activities list
 */
function onDrop(evt: MouseEvent) {
    if (dragData.value) {
        handleIncoming(dragData.value);
        currentHighlighting.value = "success";
        dragData.value = null;
        clearHighlighting();
    }
}

/**
 * Processes and submits values from the select field
 */
function setValue(val: Array<DataOption> | DataOption | null) {
    const batchMode = currentVariant.value && currentVariant.value.batch;
    if (val) {
        const values = Array.isArray(val) ? val : [val];
        const hasMapOverType = values.find((entry) => !!entry.map_over_type);
        // Match field type
        if (currentVariant.value && variant.value && values.length > 0 && values[0]) {
            const multiple = values.length > 1;
            const src = values[0].src;
            // Only match field type if source differs from current field
            if (src !== currentVariant.value.src) {
                const filteredVariant = variant.value.findIndex((v) => v.multiple === multiple && v.src === src);
                currentField.value = Math.max(filteredVariant, 0);
            }
        }
        // Emit new value
        $emit("input", {
            batch: batchMode !== BATCH.DISABLED || !!hasMapOverType,
            product: batchMode === BATCH.ENABLED && !currentLinked.value,
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

onMounted(() => {
    eventBus.$on("waiting", (value: boolean) => {
        waiting.value = value;
    });
    !isDCE.value && setValue(currentValue.value);
});

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
    <div
        :class="currentHighlighting && `ui-dragover-${currentHighlighting}`"
        @dragenter.prevent="onDragEnter"
        @dragleave.prevent="onDragLeave"
        @dragover.prevent="onDragOver"
        @drop.prevent="onDrop">
        <b-alert v-if="isDCE" variant="info" dismissible show @dismissed="currentValue = null">
            <span v-localize class="font-weight-bold">Using the following datasets (dismiss to reset):</span>
            <div v-for="(v, vIndex) of props.value.values" :key="vIndex">
                <span class="form-data-entry-label ml-2">{{ vIndex + 1 }}. {{ matchName(v) || v.id }}</span>
            </div>
        </b-alert>
        <div v-else>
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
                        <FontAwesomeIcon v-if="waiting" icon="fa-spinner" spin />
                        <span v-else class="font-weight-bold">...</span>
                    </BButton>
                </BButtonGroup>
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
                    v-model="currentLinked"
                    class="no-highlight my-2"
                    switch>
                    <div v-if="currentLinked">
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
    </div>
</template>
