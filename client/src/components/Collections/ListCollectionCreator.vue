<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faSortAlphaDown, faUndo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton } from "bootstrap-vue";
import { computed, onMounted, ref } from "vue";
import draggable from "vuedraggable";

import type { HDCADetailed, HistoryItemSummary } from "@/api";
import STATES from "@/mvc/dataset/states";
import localize from "@/utils/localization";

import CollectionCreator from "@/components/Collections/common/CollectionCreator.vue";
import DatasetCollectionElementView from "@/components/Collections/ListDatasetCollectionElementView.vue";

library.add(faSortAlphaDown, faUndo);

interface Props {
    initialElements: Array<any>;
    oncancel: () => void;
    oncreate: () => void;
    creationFn: (workingElements: any, collectionName: string, hideSourceItems: boolean) => any;
    defaultHideSourceItems?: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "clicked-create", workingElements: any, collectionName: string, hideSourceItems: boolean): void;
}>();

const state = ref("build");
const originalNamedElements = ref([]);
const duplicateNames = ref<string[]>([]);
const invalidElements = ref<string[]>([]);
const workingElements = ref<HDCADetailed[]>([]);
const selectedDatasetElements = ref<string[]>([]);
const hideSourceItems = ref(props.defaultHideSourceItems || false);

const atLeastOneDatasetIsSelected = computed(() => {
    return selectedDatasetElements.value.length > 0;
});
const getSelectedDatasetElements = computed(() => {
    return selectedDatasetElements.value;
});
const noMoreValidDatasets = computed(() => {
    return workingElements.value.length == 0;
});
const returnInvalidElementsLength = computed(() => {
    return invalidElements.value.length > 0;
});
const returnInvalidElements = computed(() => {
    return invalidElements.value;
});
const noElementsSelected = computed(() => {
    return props.initialElements.length == 0;
});
const showDuplicateError = computed(() => {
    return duplicateNames.value.length > 0;
});
const allElementsAreInvalid = computed(() => {
    return props.initialElements.length == invalidElements.value.length;
});

/** set up instance vars function */
function _instanceSetUp() {
    /** Ids of elements that have been selected by the user - to preserve over renders */
    selectedDatasetElements.value = [];
}

// ----------------------------------------------------------------------- process raw list
/** set up main data */
function _elementsSetUp() {
    /** a list of invalid elements and the reasons they aren't valid */

    invalidElements.value = [];

    //TODO: handle fundamental problem of syncing DOM, views, and list here
    /** data for list in progress */
    workingElements.value = [];

    // copy initial list, sort, add ids if needed
    workingElements.value = JSON.parse(JSON.stringify(props.initialElements.slice(0)));

    _ensureElementIds();
    _validateElements();
    _mangleDuplicateNames();
}

/** add ids to dataset objs in initial list if none */
function _ensureElementIds() {
    workingElements.value.forEach((element) => {
        if (!Object.prototype.hasOwnProperty.call(element, "id")) {
            console.warn("Element missing id", element);
        }
    });

    return workingElements.value;
}

// /** separate working list into valid and invalid elements for this collection */
function _validateElements() {
    workingElements.value = workingElements.value.filter((element) => {
        var problem = _isElementInvalid(element);

        if (problem) {
            invalidElements.value.push(element.name + "  " + problem);
        }

        return !problem;
    });

    return workingElements.value;
}

/** describe what is wrong with a particular element if anything */
function _isElementInvalid(element: HistoryItemSummary) {
    if (element.history_content_type === "dataset_collection") {
        return localize("is a collection, this is not allowed");
    }

    var validState = element.state === STATES.OK || STATES.NOT_READY_STATES.includes(element.state as string);

    if (!validState) {
        return localize("has errored, is paused, or is not accessible");
    }

    if (element.deleted || element.purged) {
        return localize("has been deleted or purged");
    }

    return null;
}

// /** mangle duplicate names using a mac-like '(counter)' addition to any duplicates */
function _mangleDuplicateNames() {
    var counter = 1;
    var existingNames: { [key: string]: boolean } = {};

    workingElements.value.forEach((element) => {
        var currName = element.name;

        while (Object.prototype.hasOwnProperty.call(existingNames, currName as string)) {
            currName = `${element.name} (${counter})`;
            counter += 1;
        }

        element.name = currName;
        existingNames[element.name as string] = true;
    });
}

function saveOriginalNames() {
    // Deep copy elements
    originalNamedElements.value = JSON.parse(JSON.stringify(workingElements.value));
}

function getOriginalNames() {
    // Deep copy elements
    workingElements.value = JSON.parse(JSON.stringify(originalNamedElements.value));
}

function elementSelected(e: HDCADetailed) {
    if (!selectedDatasetElements.value.includes(e.id)) {
        selectedDatasetElements.value.push(e.id);
    } else {
        selectedDatasetElements.value.splice(selectedDatasetElements.value.indexOf(e.id), 1);
    }
}

function elementDiscarded(e: HDCADetailed) {
    workingElements.value.splice(workingElements.value.indexOf(e), 1);

    return workingElements.value;
}

function clickClearAll() {
    selectedDatasetElements.value = [];
}

function clickedCreate(collectionName: string) {
    checkForDuplicates();

    if (state.value !== "error") {
        emit("clicked-create", workingElements.value, collectionName, hideSourceItems.value);

        return props
            .creationFn(workingElements.value, collectionName, hideSourceItems.value)
            .done(props.oncreate)
            .fail(() => {
                state.value = "error";
            });
    }
}

function checkForDuplicates() {
    var valid = true;
    var existingNames: { [key: string]: boolean } = {};

    duplicateNames.value = [];

    workingElements.value.forEach((element) => {
        if (Object.prototype.hasOwnProperty.call(existingNames, element.name as string)) {
            valid = false;
            duplicateNames.value.push(element.name as string);
        }

        existingNames[element.name as string] = true;
    });

    state.value = valid ? "build" : "error";
}

/** reset all data to the initial state */
function reset() {
    _instanceSetUp();
    getOriginalNames();
}

function sortByName() {
    workingElements.value.sort(compareNames);
}

function compareNames(a: HDCADetailed, b: HDCADetailed) {
    if (a.name && b.name && a.name < b.name) {
        return -1;
    }
    if (a.name && b.name && a.name > b.name) {
        return 1;
    }

    return 0;
}

function onUpdateHideSourceItems(newHideSourceItems: boolean) {
    hideSourceItems.value = newHideSourceItems;
}

onMounted(() => {
    _instanceSetUp();
    _elementsSetUp();
    saveOriginalNames();
});

//TODO: issue #9497
// const removeExtensions = ref(true);
// removeExtensionsToggle: function () {
//     this.removeExtensions = !this.removeExtensions;
//     if (this.removeExtensions == true) {
//         this.removeExtensionsFn();
//     }
// },
// removeExtensionsFn: function () {
//     workingElements.value.forEach((e) => {
//         var lastDotIndex = e.lastIndexOf(".");
//         if (lastDotIndex > 0) {
//             var extension = e.slice(lastDotIndex, e.length);
//             e = e.replace(extension, "");
//         }
//     });
// },
</script>

<template>
    <div class="list-collection-creator">
        <div v-if="state == 'error'">
            <BAlert show variant="danger">
                {{ localize("Galaxy could not be reached and may be updating.  Try again in a few minutes.") }}
            </BAlert>
        </div>
        <div v-else>
            <div v-if="noElementsSelected">
                <BAlert show variant="warning" dismissible>
                    {{ localize("No datasets were selected") }}
                    {{ localize("At least one element is needed for the collection. You may need to") }}
                    <a class="cancel-text" href="javascript:void(0)" role="button" @click="oncancel">
                        {{ localize("cancel") }}
                    </a>
                    {{ localize("and reselect new elements.") }}
                </BAlert>

                <div class="float-left">
                    <button class="cancel-create btn" tabindex="-1" @click="oncancel">
                        {{ localize("Cancel") }}
                    </button>
                </div>
            </div>
            <div v-else-if="allElementsAreInvalid">
                <BAlert show variant="warning" dismissible>
                    {{ localize("The following selections could not be included due to problems:") }}
                    <ul>
                        <li v-for="problem in returnInvalidElements" :key="problem">
                            {{ problem }}
                        </li>
                    </ul>
                    {{ localize("At least one element is needed for the collection. You may need to") }}
                    <a class="cancel-text" href="javascript:void(0)" role="button" @click="oncancel">
                        {{ localize("cancel") }}
                    </a>
                    {{ localize("and reselect new elements.") }}
                </BAlert>

                <div class="float-left">
                    <button class="cancel-create btn" tabindex="-1" @click="oncancel">
                        {{ localize("Cancel") }}
                    </button>
                </div>
            </div>
            <div v-else>
                <div v-if="returnInvalidElementsLength">
                    <BAlert show variant="warning" dismissible>
                        {{ localize("The following selections could not be included due to problems:") }}
                        <ul>
                            <li v-for="problem in returnInvalidElements" :key="problem">
                                {{ problem }}
                            </li>
                        </ul>
                    </BAlert>
                </div>

                <div v-if="showDuplicateError">
                    <BAlert show variant="danger">
                        {{
                            localize(
                                "Collections cannot have duplicated names. The following list names are duplicated: "
                            )
                        }}
                        <ol>
                            <li v-for="name in duplicateNames" :key="name">{{ name }}</li>
                        </ol>
                        {{ localize("Please fix these duplicates and try again.") }}
                    </BAlert>
                </div>

                <CollectionCreator
                    :oncancel="oncancel"
                    :hide-source-items="hideSourceItems"
                    @onUpdateHideSourceItems="onUpdateHideSourceItems"
                    @clicked-create="clickedCreate">
                    <template v-slot:help-content>
                        <p>
                            {{
                                localize(
                                    [
                                        "Collections of datasets are permanent, ordered lists of datasets that can be passed to tools ",
                                        "and workflows in order to have analyses done on each member of the entire group. This interface allows ",
                                        "you to create a collection and re-order the final collection.",
                                    ].join("")
                                )
                            }}
                        </p>

                        <ul>
                            <li>
                                {{ localize("Rename elements in the list by clicking on") }}
                                <i data-target=".collection-element .name">
                                    {{ localize("the existing name") }}
                                </i>
                                {{ localize(".") }}
                            </li>

                            <li>
                                {{ localize("Discard elements from the final created list by clicking on the ") }}
                                <i data-target=".collection-element .discard">
                                    {{ localize("Discard") }}
                                </i>
                                {{ localize("button.") }}
                            </li>

                            <li>
                                {{
                                    localize(
                                        "Reorder the list by clicking and dragging elements. Select multiple elements by clicking on"
                                    )
                                }}
                                <i data-target=".collection-element">
                                    {{ localize("them") }}
                                </i>
                                {{
                                    localize(
                                        "and you can then move those selected by dragging the entire group. Deselect them by clicking them again or by clicking the"
                                    )
                                }}
                                <i data-target=".clear-selected">
                                    {{ localize("Clear selected") }}
                                </i>
                                {{ localize("link.") }}
                            </li>

                            <li>
                                {{ localize("Click ") }}
                                <i data-target=".reset">
                                    <FontAwesomeIcon :icon="faUndo" />
                                </i>
                                {{ localize("to begin again as if you had just opened the interface.") }}
                            </li>

                            <li>
                                {{ localize("Click ") }}
                                <i data-target=".sort-items">
                                    <FontAwesomeIcon :icon="faSortAlphaDown" />
                                </i>
                                {{ localize("to sort datasets alphabetically.") }}
                            </li>

                            <li>
                                {{ localize("Click the") }}
                                <i data-target=".cancel-create">
                                    {{ localize("Cancel") }}
                                </i>
                                {{ localize("button to exit the interface.") }}
                            </li>
                        </ul>

                        <br />

                        <p>
                            {{ localize("Once your collection is complete, enter a ") }}
                            <i data-target=".collection-name">
                                {{ localize("name") }}
                            </i>
                            {{ localize("and click") }}
                            <i data-target=".create-collection">
                                {{ localize("Create list") }}
                            </i>
                            {{ localize(".") }}
                        </p>
                    </template>

                    <template v-slot:middle-content>
                        <div class="collection-elements-controls">
                            <BButton class="reset" :title="localize('Undo all reordering and discards')" @click="reset">
                                <FontAwesomeIcon :icon="faUndo" />
                            </BButton>

                            <BButton class="sort-items" :title="localize('Sort datasets by name')" @click="sortByName">
                                <FontAwesomeIcon :icon="faSortAlphaDown" />
                            </BButton>

                            <a
                                v-if="atLeastOneDatasetIsSelected"
                                class="clear-selected"
                                href="javascript:void(0);"
                                role="button"
                                :title="localize('De-select all selected datasets')"
                                @click="clickClearAll">
                                {{ localize("Clear selected") }}
                            </a>
                        </div>

                        <draggable
                            v-model="workingElements"
                            class="collection-elements scroll-container flex-row drop-zone"
                            @start="drag = true"
                            @end="drag = false">
                            <div v-if="noMoreValidDatasets">
                                <BAlert show variant="warning" dismissible>
                                    {{ localize("No elements left. Would you like to") }}
                                    <a class="reset-text" href="javascript:void(0)" role="button" @click="reset">
                                        {{ localize("start over") }}
                                    </a>
                                    ?
                                </BAlert>
                            </div>

                            <DatasetCollectionElementView
                                v-for="element in workingElements"
                                v-else
                                :key="element.id"
                                :class="{ selected: getSelectedDatasetElements.includes(element.id) }"
                                :element="element"
                                @element-is-selected="elementSelected"
                                @element-is-discarded="elementDiscarded"
                                @onRename="(name) => (element.name = name)" />
                        </draggable>
                    </template>
                </CollectionCreator>
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
.list-collection-creator {
    .footer {
        margin-top: 8px;
    }

    .cancel-create {
        border-color: lightgrey;
    }

    .collection-elements-controls {
        margin-bottom: 8px;

        .clear-selected {
            float: right !important;
        }
    }

    .collection-elements {
        max-height: 400px;
        border: 0px solid lightgrey;
        overflow-y: auto;
        overflow-x: hidden;
    }

    // TODO: taken from .dataset above - swap these out
    .collection-element {
        height: 32px;
        margin: 2px 4px 0px 4px;
        opacity: 1;
        border: 1px solid lightgrey;
        border-radius: 3px;
        padding: 0 8px 0 8px;
        line-height: 28px;
        cursor: pointer;
        overflow: hidden;

        &:last-of-type {
            margin-bottom: 2px;
        }

        &:hover {
            border-color: black;
        }

        &.selected {
            border-color: black;
            background: rgb(118, 119, 131);
            color: white;
            a {
                color: white;
            }
        }

        .name {
            &:hover {
                text-decoration: underline;
            }
        }

        button {
            margin-top: 3px;
        }

        .discard {
            @extend .float-right !optional;
        }
    }

    .empty-message {
        margin: 8px;
        color: grey;
        font-style: italic;
        text-align: center;
    }
}
</style>
