<script setup lang="ts">
import {
    faCaretDown,
    faCaretUp,
    faExclamation,
    faLink,
    faPlus,
    faSpinner,
    faUnlink,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BButtonGroup, BCollapse, BFormCheckbox, BTooltip } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onMounted, type Ref, ref, watch } from "vue";

import {
    type DCESummary,
    type HDAObject,
    type HistoryItemSummary,
    isDatasetElement,
    isDCE,
    isHDCA,
    isHistoryItem,
} from "@/api";
import type { HistoryContentType } from "@/api/datasets";
import { getGalaxyInstance } from "@/app";
import { useDatatypesMapper } from "@/composables/datatypesMapper";
import { useUid } from "@/composables/utils/uid";
import { type EventData, useEventStore } from "@/stores/eventStore";
import { useHistoryStore } from "@/stores/historyStore";
import { orList } from "@/utils/strings";

import type { DataOption } from "./types";
import { containsDataOption } from "./types";
import { BATCH, SOURCE, VARIANTS } from "./variants";

import FormSelection from "../FormSelection.vue";
import CollectionCreatorModal from "@/components/Collections/CollectionCreatorModal.vue";
import FormSelect from "@/components/Form/Elements/FormSelect.vue";
import HelpText from "@/components/Help/HelpText.vue";

const COLLECTION_TYPE_TO_LABEL: Record<string, string> = {
    list: "list",
    "list:paired": "list of dataset pairs",
    paired: "dataset pair",
};

type SelectOption = {
    label: string;
    value: DataOption | null;
};

type HistoryOrCollectionItem = HistoryItemSummary | DCESummary;

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
        type?: "data" | "data_collection";
        collectionTypes?: Array<string>;
        flavor?: string;
        tag?: string;
    }>(),
    {
        loading: false,
        multiple: false,
        optional: false,
        value: undefined,
        extensions: () => [],
        type: "data",
        collectionTypes: undefined,
        flavor: undefined,
        tag: undefined,
    }
);

const eventStore = useEventStore();
const { datatypesMapper } = useDatatypesMapper();

const $emit = defineEmits(["input", "alert"]);

// Determines wether values should be processed as linked or unlinked
const currentLinked = ref(true);

// Indicates which of the select field from the set of variants is currently shown
const currentField = ref(0);

// Field highlighting status
const currentHighlighting: Ref<string | null> = ref(null);

// Drag/Drop related values
const dragData: Ref<EventData[]> = ref([]);
const dragTarget: Ref<EventTarget | null> = ref(null);

// Collection creator modal settings
const collectionModalShow = ref(false);
const collectionModalType = ref<"list" | "list:paired" | "paired">("list");
const { currentHistoryId } = storeToRefs(useHistoryStore());
const restrictsExtensions = computed(() => {
    const extensions = props.extensions;
    if (!extensions || extensions.length == 0 || extensions.indexOf("data") >= 0) {
        return false;
    } else {
        return true;
    }
});

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
        if (!currentVariant.value?.multiple && !props.optional && formattedOptions.value.length > 0) {
            const firstEntry = formattedOptions.value && formattedOptions.value[0];
            if (firstEntry && firstEntry.value) {
                value.push(firstEntry.value);
                return value;
            }
        }
        return undefined;
    },
    set: (val) => {
        if (val && Array.isArray(val) && val.length > 0) {
            val.sort((a, b) => {
                const aHid = a.hid;
                const bHid = b.hid;
                if (aHid && bHid) {
                    return aHid - bHid;
                } else {
                    return 0;
                }
            });
        }
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
function createValue(val?: Array<DataOption> | DataOption | null) {
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
function handleIncoming(incoming: Record<string, unknown> | Record<string, unknown>[], partial = true) {
    if (incoming) {
        const values = Array.isArray(incoming) ? incoming : [incoming];

        // ensure all incoming values are isHistoryOrCollectionItem
        if (!values.every(isHistoryOrCollectionItem)) {
            return false;
        }

        const extensions = Array.from(
            new Set(
                values
                    .map(getExtensionsForItem)
                    .flat()
                    .filter((v) => v !== null && v !== undefined)
            )
        ) as string[];

        if (!canAcceptDatatype(extensions)) {
            return false;
        }
        if (
            values.some((v) => {
                const { historyContentType } = getSrcAndContentType(v);
                const collectionType = "collection_type" in v && v.collection_type ? v.collection_type : undefined;
                return !canAcceptSrc(historyContentType, collectionType);
            })
        ) {
            return false;
        }
        if (values.length > 0) {
            const incomingValues: Array<DataOption> = [];
            values.forEach((currVal) => {
                // Map incoming objects to data option values
                const newValue = toDataOption(currVal);
                if (!newValue) {
                    return false;
                }
                // Verify that new value has corresponding option
                const keepKey = `${newValue.id}_${newValue.src}`;
                const existingOptions = props.options && props.options[newValue.src];
                const foundOption = existingOptions && existingOptions.find((option) => option.id === newValue.id);
                if (!foundOption && !(keepKey in keepOptions)) {
                    keepOptions[keepKey] = {
                        label: `${newValue.hid || "Selected"}: ${newValue.name}`,
                        value: newValue,
                    };
                }
                // Add new value to list
                incomingValues.push(newValue);
            });
            let hasDuplicates = false;
            if (incomingValues.length > 0 && incomingValues[0]) {
                // Set new value
                const config = currentVariant.value;
                const firstValue = incomingValues[0];
                if (config && config.src == firstValue.src && partial) {
                    if (config.multiple) {
                        const newValues = currentValue.value ? currentValue.value.slice() : [];
                        incomingValues.forEach((v) => {
                            if (containsDataOption(newValues, v)) {
                                hasDuplicates = true;
                            } else {
                                newValues.push(v);
                            }
                        });
                        currentValue.value = newValues;
                    } else {
                        if (containsDataOption(currentValue.value ?? [], firstValue)) {
                            hasDuplicates = true;
                        }
                        currentValue.value = [firstValue];
                    }
                } else {
                    currentValue.value = incomingValues;
                }
            }
            if (hasDuplicates) {
                return false;
            }
        }
    }
    return true;
}

function toDataOption(item: HistoryOrCollectionItem): DataOption | null {
    const { newSrc, datasetCollectionDataset } = getSrcAndContentType(item);
    let v: HistoryOrCollectionItem | HDAObject;
    if (datasetCollectionDataset) {
        v = datasetCollectionDataset;
    } else {
        v = item;
    }
    const newHid = isHistoryItem(v) ? v.hid : undefined;
    const newId = v.id;
    const newName = isHistoryItem(v) && v.name ? v.name : newId;
    const newValue: DataOption = {
        id: newId,
        src: newSrc,
        batch: false,
        map_over_type: undefined,
        hid: newHid,
        name: newName,
        keep: true,
        tags: [],
    };
    if (isHistoryItem(v) && isHDCA(v) && props.collectionTypes?.length > 0) {
        const itemCollectionType = v.collection_type;
        if (!props.collectionTypes.includes(itemCollectionType)) {
            const mapOverType = props.collectionTypes.find((collectionType) =>
                itemCollectionType.endsWith(collectionType)
            );
            if (!mapOverType) {
                return null;
            }
            newValue["batch"] = true;
            newValue["map_over_type"] = mapOverType;
        }
    }
    return newValue;
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

function canAcceptDatatype(itemDatatypes: string | Array<string>) {
    // TODO: Shouldn't we enforce a datatype (at least "data") because of the case:
    // What if the drop item is a `DCESummary`, then it has no extension (?) and we
    // pass it as a valid item regardless of its elements' datatypes.
    if (!(props.extensions?.length > 0) || props.extensions.includes("data")) {
        return true;
    }
    let datatypes: Array<string>;
    if (!Array.isArray(itemDatatypes)) {
        datatypes = [itemDatatypes];
    } else {
        datatypes = itemDatatypes;
    }
    const incompatibleItem = datatypes.find(
        (extension) => !datatypesMapper.value?.isSubTypeOfAny(extension, props.extensions)
    );
    if (incompatibleItem) {
        return false;
    }
    return true;
}

/**
 * Given an element, determine the source and content type.
 * Also returns the collection element dataset object if it exists.
 */
function getSrcAndContentType(element: HistoryOrCollectionItem): {
    historyContentType: HistoryContentType;
    newSrc: string;
    datasetCollectionDataset: HDAObject | undefined;
} {
    let historyContentType: HistoryContentType;
    let newSrc: string;
    let datasetCollectionDataset: HDAObject | undefined;
    if (isDCE(element)) {
        if (isDatasetElement(element)) {
            historyContentType = "dataset";
            newSrc = SOURCE.DATASET;
            datasetCollectionDataset = element.object;
        } else {
            historyContentType = "dataset_collection";
            newSrc = SOURCE.COLLECTION_ELEMENT;
        }
    } else {
        historyContentType = element.history_content_type;
        newSrc =
            "src" in element && typeof element.src === "string"
                ? element.src
                : historyContentType === "dataset_collection"
                ? SOURCE.COLLECTION
                : SOURCE.DATASET;
    }
    return { historyContentType, newSrc, datasetCollectionDataset };
}

function canAcceptSrc(historyContentType: "dataset" | "dataset_collection", collectionType?: string) {
    if (historyContentType === "dataset") {
        // HDA can only be fed into data parameters, not collection parameters
        if (props.type === "data") {
            return true;
        } else {
            $emit("alert", "dataset is not a valid input for dataset collection parameter.");
            return false;
        }
    } else if (historyContentType === "dataset_collection") {
        if (props.type === "data") {
            // collection can always be mapped over a data input ... in theory.
            // One day we should also validate the map over model
            return true;
        }
        if (!collectionType) {
            // Should always be set if item is dataset collection
            throw Error("Item is a dataset collection of unknown type.");
        } else if (!props.collectionTypes) {
            // if no collection_type is set all collections are valid
            return true;
        } else {
            if (props.collectionTypes.includes(collectionType)) {
                return true;
            }
            if (props.collectionTypes.some((element) => collectionType.endsWith(element))) {
                return true;
            } else {
                $emit(
                    "alert",
                    `${collectionType} dataset collection is not a valid input for ${orList(
                        props.collectionTypes
                    )} type dataset collection parameter.`
                );
                return false;
            }
        }
    } else {
        throw Error("Unknown history content type.");
    }
}

/** Allowed collection types for collection creation */
const effectiveCollectionTypes = props.collectionTypes?.filter((collectionType) =>
    ["list", "list:paired", "paired"].includes(collectionType)
);

function buildNewCollection(collectionType: string) {
    if (!["list", "list:paired", "paired"].includes(collectionType)) {
        throw Error(`Unknown collection type: ${collectionType}`);
    }
    collectionModalType.value = collectionType as "list" | "list:paired" | "paired";
    collectionModalShow.value = true;
}

function createdCollection(collection: any) {
    handleIncoming(collection);
}

/**
 * Get the extension(s) for a given item
 */
function getExtensionsForItem(item: HistoryOrCollectionItem): string | string[] | null {
    return "extension" in item ? item.extension : "elements_datatypes" in item ? item.elements_datatypes : null;
}

function isHistoryOrCollectionItem(item: EventData): item is HistoryOrCollectionItem {
    return isHistoryItem(item) || isDCE(item);
}

function getNameForItem(item: HistoryOrCollectionItem): string {
    if (isHistoryItem(item)) {
        return item.name ?? `Item ${item.hid}`;
    } else if (isDCE(item)) {
        return item.element_identifier;
    } else {
        throw new Error("Unknown item type");
    }
}

// Drag/Drop event handlers
function onDragEnter(evt: MouseEvent) {
    const eventData = eventStore.getDragItems();
    dragData.value = [];

    for (const item of eventData) {
        if (isHistoryOrCollectionItem(item)) {
            const extensions = getExtensionsForItem(item);
            const { historyContentType } = getSrcAndContentType(item);
            const collectionType = "collection_type" in item && item.collection_type ? item.collection_type : undefined;
            let highlightingState = "success";
            if (extensions && !canAcceptDatatype(extensions)) {
                highlightingState = "warning";
                $emit("alert", `${extensions} is not an acceptable format for this parameter.`);
            } else if (!canAcceptSrc(historyContentType, collectionType)) {
                highlightingState = "warning";
                $emit("alert", `${historyContentType} is not an acceptable input type for this parameter.`);
            }
            // Check if the item is already in the current value
            const option = toDataOption(item);
            const isAlreadyInValue = containsDataOption(currentValue.value ?? [], option);
            if (isAlreadyInValue) {
                highlightingState = "warning";
                $emit("alert", `${getNameForItem(item)} is already selected.`);
            }

            currentHighlighting.value = highlightingState;
            dragTarget.value = evt.target;
            dragData.value.push(item);
        }
    }
}

function onDragLeave(evt: MouseEvent) {
    if (dragTarget.value === evt.target) {
        currentHighlighting.value = null;
        $emit("alert", undefined);
    }
}

function onDrop() {
    if (dragData.value.length) {
        if (handleIncoming(dragData.value, dragData.value.length === 1)) {
            currentHighlighting.value = "success";
        } else {
            currentHighlighting.value = "warning";
        }
        $emit("alert", undefined);
        dragData.value = [];
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
                    const accepted = !props.tag || option.tags?.includes(props.tag);
                    if (accepted) {
                        values.push({ ...option, name: option.name || entry.id });
                    }
                }
            }
        });
    }
    return values;
});

onMounted(() => {
    if (props.value && matchedValues.value.length > 0) {
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

const formatsVisible = ref(false);
const formatsButtonId = useUid("form-data-formats-");

function collectionTypeToText(collectionType: string): string {
    if (collectionType == "list:paired") {
        return "list of pairs";
    } else {
        return collectionType;
    }
}

const warningListAmount = 4;
const noOptionsWarningMessage = computed(() => {
    const itemType = props.type === "data" ? "datasets" : "dataset collections";
    const collectionTypeLabel = props.collectionTypes?.length
        ? `${orList(props.collectionTypes.map(collectionTypeToText))} `
        : "";
    if (!props.extensions || props.extensions.length === 0 || props.extensions.includes("data")) {
        return `No ${collectionTypeLabel}${itemType} available`;
    } else if (props.extensions.length <= warningListAmount) {
        return `No ${collectionTypeLabel}${itemType} with ${orList(props.extensions)} elements available`;
    } else {
        return `No compatible ${collectionTypeLabel}${itemType} available`;
    }
});
</script>

<template>
    <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions -->
    <div
        class="form-data"
        :class="currentHighlighting && `ui-dragover-${currentHighlighting}`"
        @dragenter.prevent="onDragEnter"
        @dragleave.prevent="onDragLeave"
        @dragover.prevent
        @drop.prevent="onDrop">
        <div class="d-flex flex-column">
            <BButtonGroup v-if="variant && variant.length > 1" buttons class="align-self-start">
                <BButton
                    v-for="(v, index) in variant"
                    :key="index"
                    v-b-tooltip.hover.bottom
                    :pressed="currentField === index"
                    :title="v.tooltip"
                    @click="currentField = index">
                    <FontAwesomeIcon :icon="['far', v.icon]" />
                </BButton>
                <BButton v-if="canBrowse" v-b-tooltip.hover.bottom title="Browse or Upload Datasets" @click="onBrowse">
                    <FontAwesomeIcon v-if="loading" :icon="faSpinner" spin />
                    <span v-else class="font-weight-bold">...</span>
                </BButton>
                <BButtonGroup v-if="effectiveCollectionTypes?.length > 0" size="sm" buttons>
                    <BButton
                        v-for="collectionType in effectiveCollectionTypes"
                        :key="collectionType"
                        v-b-tooltip.hover.bottom
                        :title="`Create a new ${COLLECTION_TYPE_TO_LABEL[collectionType]}`"
                        :variant="formattedOptions.length === 0 ? 'warning' : 'secondary'"
                        @click="buildNewCollection(collectionType)">
                        <FontAwesomeIcon :icon="faPlus" fixed-width />
                    </BButton>
                </BButtonGroup>
            </BButtonGroup>
            <div v-if="restrictsExtensions">
                <BButton :id="formatsButtonId" class="ui-link" @click="formatsVisible = !formatsVisible">
                    accepted formats
                    <FontAwesomeIcon v-if="formatsVisible" :icon="faCaretUp" />
                    <FontAwesomeIcon v-else :icon="faCaretDown" />
                </BButton>
                <BCollapse v-model="formatsVisible">
                    <ul class="pl-3 m-0">
                        <li v-for="extension in extensions" :key="extension">{{ extension }}</li>
                    </ul>
                </BCollapse>
                <BTooltip :target="formatsButtonId" noninteractive placement="bottom" triggers="hover">
                    <div class="form-data-extensions-tooltip">
                        <span v-for="extension in extensions" :key="extension">{{ extension }}</span>
                    </div>
                </BTooltip>
            </div>
        </div>

        <FormSelect
            v-if="currentVariant && !currentVariant.multiple"
            v-model="currentValue"
            class="align-self-start"
            :multiple="currentVariant.multiple"
            :optional="currentVariant.multiple || optional"
            :options="formattedOptions"
            :placeholder="`Select a ${placeholder}`">
            <template v-slot:no-options>
                <BAlert class="w-100 align-items-center" variant="warning" show>
                    {{ noOptionsWarningMessage }}
                </BAlert>
            </template>
        </FormSelect>
        <FormSelection
            v-else-if="currentVariant?.multiple"
            v-model="currentValue"
            :data="formattedOptions"
            optional
            multiple />

        <CollectionCreatorModal
            v-if="currentHistoryId && effectiveCollectionTypes?.length > 0"
            :history-id="currentHistoryId"
            :collection-type="collectionModalType"
            :extensions="props.extensions.filter((ext) => ext !== 'data')"
            :show-modal.sync="collectionModalShow"
            @created-collection="createdCollection" />

        <template v-if="currentVariant && currentVariant.batch !== BATCH.DISABLED">
            <BFormCheckbox
                v-if="currentVariant.batch === BATCH.ENABLED"
                v-model="currentLinked"
                class="checkbox no-highlight"
                switch>
                <span v-if="currentLinked">
                    <FontAwesomeIcon :icon="faLink" />
                    <b v-localize class="mr-1">Linked:</b>
                    <span v-localize>Datasets will be run in matched order with other datasets.</span>
                </span>
                <span v-else>
                    <FontAwesomeIcon :icon="faUnlink" />
                    <b v-localize class="mr-1">Unlinked:</b>
                    <span v-localize>Dataset will be run against *all* other datasets.</span>
                </span>
            </BFormCheckbox>
            <div class="info text-info">
                <FontAwesomeIcon :icon="faExclamation" />
                <span v-if="props.type == 'data' && currentVariant.src == SOURCE.COLLECTION" class="ml-1">
                    The supplied input will be <HelpText text="mapped over" uri="galaxy.collections.mapOver" /> this
                    tool.
                </span>
                <span v-else v-localize class="ml-1">
                    This is a batch mode input field. Individual jobs will be triggered for each dataset.
                </span>
            </div>
        </template>
    </div>
</template>

<style scoped lang="scss">
.form-data {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.5rem;

    .checkbox {
        grid-column: span 2;
    }

    .info {
        grid-column: span 2;
    }
}
</style>

<style lang="scss">
.form-data-extensions-tooltip {
    display: flex;
    flex-wrap: wrap;
    column-gap: 0.25rem;
    font-size: 0.8rem;

    span::after {
        content: ", ";
    }

    span:last-child::after {
        content: none;
    }
}
</style>
