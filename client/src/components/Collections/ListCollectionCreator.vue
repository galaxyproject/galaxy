<script setup lang="ts">
import "ui/hoverhighlight";

import { faSquare } from "@fortawesome/free-regular-svg-icons";
import { faMinus, faSortAlphaDown, faTimes, faUndo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { computed, ref, watch } from "vue";
import draggable from "vuedraggable";

import type { CollectionElementIdentifiers, CreateNewCollectionPayload, HDASummary, HistoryItemSummary } from "@/api";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { Toast } from "@/composables/toast";
import localize from "@/utils/localization";

import { stripExtension, useUpdateIdentifiersForRemoveExtensions } from "./common/stripExtension";
import { type Mode, useCollectionCreator } from "./common/useCollectionCreator";

import GButton from "../BaseComponents/GButton.vue";
import GButtonGroup from "../BaseComponents/GButtonGroup.vue";
import FormSelectMany from "../Form/Elements/FormSelectMany/FormSelectMany.vue";
import HelpText from "../Help/HelpText.vue";
import CollectionCreator from "@/components/Collections/common/CollectionCreator.vue";
import DatasetCollectionElementView from "@/components/Collections/ListDatasetCollectionElementView.vue";

const NOT_VALID_ELEMENT_MSG: string = localize("is not a valid element for this collection");

interface Props {
    historyId: string;
    initialElements: HistoryItemSummary[];
    defaultHideSourceItems?: boolean;
    suggestedName?: string;
    fromSelection?: boolean;
    extensions?: string[];
    mode: Mode;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "on-create", options: CreateNewCollectionPayload): void;
    (e: "on-cancel"): void;
    (e: "name", value: string): void;
    (e: "input-valid", value: boolean): void;
}>();

const state = ref("build");
const duplicateNames = ref<string[]>([]);
const invalidElements = ref<string[]>([]);
const workingElements = ref<HDASummary[]>([]);
const selectedDatasetElements = ref<string[]>([]);
const atLeastOneElement = ref(true);

const { updateIdentifierIfUnchanged } = useUpdateIdentifiersForRemoveExtensions(props);

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
const noInitialElements = computed(() => {
    return props.initialElements.length == 0;
});
const showDuplicateError = computed(() => {
    return duplicateNames.value.length > 0;
});
const allElementsAreInvalid = computed(() => {
    return props.initialElements.length == invalidElements.value.length;
});

/** If not `fromSelection`, the list of elements that will become the collection */
const inListElements = ref<HDASummary[]>([]);

/** Does `inListElements` have elements with different extensions? */
const listHasMixedExtensions = computed(() => {
    const extensions = new Set(inListElements.value.map((e) => e.extension));
    return extensions.size > 1;
});
const {
    removeExtensions,
    hideSourceItems,
    onUpdateHideSourceItems,
    isElementInvalid,
    collectionName,
    onUpdateCollectionName,
    onCollectionCreate,
    showElementExtension,
    showButtonsForModal,
    showHid,
} = useCollectionCreator(props, emit);

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

    // reverse the order of the elements to emulate what we have in the history panel
    workingElements.value.reverse();

    if (removeExtensions.value) {
        workingElements.value.forEach((el) => {
            if (el.name) {
                el.name = stripExtension(el.name);
            }
        });
    } else {
        //
    }

    // for inListElements, reset their values (in order) to datasets from workingElements
    const inListElementsPrev = inListElements.value;
    inListElements.value = [];
    inListElementsPrev.forEach((prevElem) => {
        const matchingElem = workingElements.value.find((e) => e.id === prevElem.id);

        if (matchingElem) {
            const problem = isElementInvalid(matchingElem);
            if (problem) {
                const invalidMsg = `${prevElem.hid}: ${prevElem.name} ${problem} and ${NOT_VALID_ELEMENT_MSG}`;
                Toast.error(invalidMsg, localize("Invalid element"));
            } else {
                inListElements.value.push(matchingElem);
            }
        } else {
            const invalidMsg = `${prevElem.hid}: ${prevElem.name} ${localize("has been removed from the collection")}`;
            Toast.error(invalidMsg, localize("Invalid element"));
        }
    });

    // _ensureElementIds();
    _validateElements();
    _mangleDuplicateNames();
}

// TODO: not sure if this is needed
// function _ensureElementIds() {
//     workingElements.value.forEach((element) => {
//         if (!Object.prototype.hasOwnProperty.call(element, "id")) {
//             console.warn("Element missing id", element);
//         }
//     });

//     return workingElements.value;
// }

// /** separate working list into valid and invalid elements for this collection */
function _validateElements() {
    workingElements.value = workingElements.value.filter((element) => {
        var problem = isElementInvalid(element);

        if (problem) {
            invalidElements.value.push(element.name + "  " + problem);
        }

        return !problem;
    });

    return workingElements.value;
}

function removeExtensionsToggle() {
    removeExtensions.value = !removeExtensions.value;
    const removeExtensionsValue = removeExtensions.value;
    workingElements.value.forEach((el) => {
        updateIdentifierIfUnchanged(el, removeExtensionsValue);
    });
    _mangleDuplicateNames();
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

function changeDatatypeFilter(newFilter: "all" | "datatype" | "ext") {
    _elementsSetUp();
}

function elementSelected(e: HDASummary) {
    if (!selectedDatasetElements.value.includes(e.id)) {
        selectedDatasetElements.value.push(e.id);
    } else {
        selectedDatasetElements.value.splice(selectedDatasetElements.value.indexOf(e.id), 1);
    }
}

function elementDiscarded(e: HDASummary) {
    workingElements.value.splice(workingElements.value.indexOf(e), 1);
    selectedDatasetElements.value = selectedDatasetElements.value.filter((element) => {
        return element !== e.id;
    });

    return workingElements.value;
}

function clickClearAll() {
    selectedDatasetElements.value = [];
}

function clickRemoveSelected() {
    workingElements.value = workingElements.value.filter((element) => {
        return !selectedDatasetElements.value.includes(element.id);
    });

    selectedDatasetElements.value = [];
}

function clickSelectAll() {
    selectedDatasetElements.value = workingElements.value.map((element) => {
        return element.id;
    });
}
const { confirm } = useConfirmDialog();

async function attemptCreate() {
    checkForDuplicates();

    const returnedElements = props.fromSelection ? workingElements.value : inListElements.value;
    atLeastOneElement.value = returnedElements.length > 0;

    let confirmed = false;
    if (!atLeastOneElement.value) {
        confirmed = await confirm("Are you sure you want to create a list with no datasets?", {
            title: "Create an empty list",
            okTitle: "Create",
            okVariant: "primary",
        });
    }

    if (state.value !== "error" && (atLeastOneElement.value || confirmed)) {
        const identifiers = returnedElements.map((element) => ({
            id: element.id,
            name: element.name,
            //TODO: this allows for list:list even if the implementation does not - reconcile
            src: "src" in element ? element.src : element.history_content_type == "dataset" ? "hda" : "hdca",
        })) as CollectionElementIdentifiers;
        onCollectionCreate("list", identifiers);
    }
}

defineExpose({ attemptCreate });

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
    /** Ids of elements that have been selected by the user - to preserve over renders */
    selectedDatasetElements.value = [];
    _elementsSetUp();
}

function sortByName() {
    workingElements.value.sort(compareNames);
}

function compareNames(a: HDASummary, b: HDASummary) {
    if (a.name && b.name && a.name < b.name) {
        return -1;
    }
    if (a.name && b.name && a.name > b.name) {
        return 1;
    }

    return 0;
}

watch(
    () => props.initialElements,
    () => {
        // for any new/removed elements, add them to working elements
        _elementsSetUp();
    },
    { immediate: true }
);

function addUploadedFiles(files: HDASummary[]) {
    const returnedElements = props.fromSelection ? workingElements : inListElements;
    files.forEach((f) => {
        const file = props.fromSelection ? f : workingElements.value.find((e) => e.id === f.id);
        const problem = isElementInvalid(f);
        if (file && !returnedElements.value.find((e) => e.id === file.id)) {
            returnedElements.value.push(file);
        } else if (problem) {
            invalidElements.value.push("Uploaded item: " + f.name + "  " + problem);
            Toast.error(
                localize(`Dataset ${f.hid}: ${f.name} ${problem} and is an invalid element for this collection`),
                localize("Uploaded item is invalid")
            );
        } else if (!file) {
            invalidElements.value.push("Uploaded item: " + f.name + " could not be added to the collection");
            Toast.error(
                localize(`Dataset ${f.hid}: ${f.name} could not be added to the collection`),
                localize("Uploaded item is invalid")
            );
        }
    });
}

/** find the element in the workingElements array and update its name */
function renameElement(element: any, name: string) {
    // We do this whole process of removing and readding because, in the case that the element
    // is in the list, inListElements might be reacting to changes in workingElements, and we
    // want to prevent that from causing issues with producing duplicate elements in either array:

    // first check at what index of inlistElements the element is
    const index = inListElements.value.findIndex((e) => e.id === element.id);
    if (index >= 0) {
        // remove from inListElements
        inListElements.value = inListElements.value.filter((e) => e.id !== element.id);
    }

    // then find the element in workingElements, and rename it
    element = workingElements.value.find((e) => e.id === element.id);
    if (element) {
        element.name = name;
    }

    // now add again to inListElements at same index
    if (index >= 0) {
        inListElements.value.splice(index, 0, element);
    }
}

function selectionAsHdaSummary(value: any): HDASummary {
    return value as HDASummary;
}
</script>

<template>
    <div class="list-collection-creator">
        <div v-if="!showDuplicateError && state == 'error'">
            <BAlert show variant="danger">
                {{ localize("There was a problem creating the collection.") }}
            </BAlert>
        </div>
        <div v-else>
            <div v-if="fromSelection && returnInvalidElementsLength">
                <BAlert show variant="warning" dismissible>
                    {{ localize("The following selections could not be included due to problems:") }}
                    <ul>
                        <li v-for="problem in returnInvalidElements" :key="problem">
                            {{ problem }}
                        </li>
                    </ul>
                </BAlert>
            </div>

            <div v-if="!atLeastOneElement">
                <BAlert show variant="warning" dismissible @dismissed="atLeastOneElement = true">
                    {{ localize("At least one element is needed for the list.") }}
                    <span v-if="fromSelection">
                        <a class="cancel-text" href="javascript:void(0)" role="button" @click="emit('on-cancel')">
                            {{ localize("Cancel") }}
                        </a>
                        {{ localize("and reselect new elements.") }}
                    </span>
                </BAlert>
            </div>

            <div v-if="showDuplicateError">
                <BAlert show variant="danger">
                    {{
                        localize("Collections cannot have duplicated names. The following list names are duplicated: ")
                    }}
                    <ol>
                        <li v-for="name in duplicateNames" :key="name">{{ name }}</li>
                    </ol>
                    {{ localize("Please fix these duplicates and try again.") }}
                </BAlert>
            </div>

            <CollectionCreator
                :oncancel="() => emit('on-cancel')"
                :history-id="props.historyId"
                :hide-source-items="hideSourceItems"
                render-extensions-toggle
                :extensions-toggle="removeExtensions"
                :extensions="extensions"
                collection-type="list"
                :no-items="props.initialElements.length == 0 && !props.fromSelection"
                :show-upload="!fromSelection"
                :suggested-name="props.suggestedName"
                :show-buttons="showButtonsForModal"
                :collection-name="collectionName"
                :mode="mode"
                @on-update-collection-name="onUpdateCollectionName"
                @add-uploaded-files="addUploadedFiles"
                @on-update-datatype-toggle="changeDatatypeFilter"
                @onUpdateHideSourceItems="onUpdateHideSourceItems"
                @remove-extensions-toggle="removeExtensionsToggle"
                @clicked-create="attemptCreate">
                <template v-slot:help-content>
                    <p>
                        {{
                            localize(
                                [
                                    "This interface allows you to build a new Galaxy list of datasets. ",
                                    "A list is a type of Galaxy dataset collection that is a permanent, ordered list of datasets that can be passed to tools ",
                                    "and workflows in order to have analyses done on each member of the entire group. This interface allows ",
                                    "you to create and re-order a list of datasets. The datasets in a Galaxy collection have an identifier that is preserved accross ",
                                    "tool executions and serves as a form of sample tracking - setting the name in this form will pick the identifier for that element ",
                                    "of the list but will not change the dataset's actual name in Galaxy.",
                                ].join("")
                            )
                        }}
                    </p>

                    <ul>
                        <li v-if="!fromSelection">
                            Move datasets from the "Unselected" column to the "Selected" column below to compose the
                            list in the intended order and with the intended datasets.
                        </li>
                        <li v-if="!fromSelection">
                            The filter textbox can be used to rapidly find the datasets of interest by name.
                        </li>
                        <li>
                            {{ localize("Change the identifier of elements in the list by clicking on") }}
                            <i data-target=".collection-element .name">
                                {{ localize("the existing name") }}
                            </i>
                            {{ localize("in either column.") }}
                        </li>

                        <li>
                            {{ localize("Discard elements from the final created list by clicking on the ") }}
                            <i v-if="fromSelection" data-target=".collection-element .discard">
                                {{ localize("Remove") }}
                            </i>
                            <i v-else data-target=".collection-element .discard">
                                {{ localize("discard") }}
                            </i>
                            {{ localize("button.") }}
                        </li>

                        <li v-if="fromSelection">
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

                        <li v-if="fromSelection">
                            {{ localize("Click ") }}
                            <i data-target=".reset">
                                <FontAwesomeIcon :icon="faUndo" />
                            </i>
                            {{ localize("to begin again as if you had just opened the interface.") }}
                        </li>

                        <li v-if="fromSelection">
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
                    <BAlert v-if="listHasMixedExtensions" show variant="warning" dismissible>
                        {{ localize("The selected datasets have mixed formats.") }}
                        {{ localize("You can still create the list but generally") }}
                        {{ localize("dataset lists should contain datasets of the same type.") }}
                        <HelpText
                            uri="galaxy.collections.collectionBuilder.whyHomogenousCollections"
                            :text="localize('Why?')" />
                    </BAlert>
                    <div v-if="noInitialElements">
                        <BAlert show variant="warning" dismissible>
                            {{ localize("No datasets were selected") }}
                            {{ localize("At least one element is needed for the collection. You may need to") }}
                            <a class="cancel-text" href="javascript:void(0)" role="button" @click="emit('on-cancel')">
                                {{ localize("cancel") }}
                            </a>
                            {{ localize("and reselect new elements, or upload datasets.") }}
                        </BAlert>
                    </div>
                    <div v-else-if="allElementsAreInvalid">
                        <BAlert v-if="!fromSelection" show variant="warning">
                            {{
                                localize(
                                    "No elements in your history are valid for this list. \
                                    You may need to switch to a different history or upload valid datasets."
                                )
                            }}
                            <div v-if="extensions?.length">
                                {{ localize("The following format(s) are required for this list: ") }}
                                <ul>
                                    <li v-for="extension in extensions" :key="extension">
                                        {{ extension }}
                                    </li>
                                </ul>
                            </div>
                        </BAlert>
                        <BAlert v-else show variant="warning" dismissible>
                            {{ localize("The following selections could not be included due to problems:") }}
                            <ul>
                                <li v-for="problem in returnInvalidElements" :key="problem">
                                    {{ problem }}
                                </li>
                            </ul>
                            {{ localize("At least one element is needed for the collection. You may need to") }}
                            <a class="cancel-text" href="javascript:void(0)" role="button" @click="emit('on-cancel')">
                                {{ localize("cancel") }}
                            </a>
                            {{ localize("and reselect new elements, or upload valid datasets.") }}
                        </BAlert>
                    </div>
                    <div v-else-if="fromSelection">
                        <div class="collection-elements-controls">
                            <div>
                                <GButton
                                    class="reset"
                                    :title="localize('Reset to original state')"
                                    size="small"
                                    @click="reset">
                                    <FontAwesomeIcon :icon="faUndo" fixed-width />
                                    {{ localize("Reset") }}
                                </GButton>
                                <GButton
                                    class="sort-items"
                                    :title="localize('Sort datasets by name')"
                                    size="small"
                                    @click="sortByName">
                                    <FontAwesomeIcon :icon="faSortAlphaDown" />
                                </GButton>
                            </div>

                            <div class="center-text">
                                <u>{{ workingElements.length }}</u> {{ localize("elements in list") }}
                            </div>

                            <div>
                                <span v-if="atLeastOneDatasetIsSelected">
                                    {{ localize("For selection") }} ({{ selectedDatasetElements.length }}):
                                </span>
                                <GButtonGroup>
                                    <GButton
                                        v-if="atLeastOneDatasetIsSelected"
                                        :title="localize('Remove selected datasets from the list')"
                                        size="small"
                                        @click="clickRemoveSelected">
                                        <FontAwesomeIcon :icon="faMinus" fixed-width />
                                        {{ localize("Remove") }}
                                    </GButton>
                                    <GButton
                                        v-if="
                                            !atLeastOneDatasetIsSelected ||
                                            selectedDatasetElements.length < workingElements.length
                                        "
                                        :title="localize('Select all datasets')"
                                        size="small"
                                        @click="clickSelectAll">
                                        <FontAwesomeIcon :icon="faSquare" fixed-width />
                                        {{ localize("Select all") }}
                                    </GButton>
                                    <GButton
                                        v-if="atLeastOneDatasetIsSelected"
                                        class="clear-selected"
                                        :title="localize('De-select all selected datasets')"
                                        size="small"
                                        @click="clickClearAll">
                                        <FontAwesomeIcon :icon="faTimes" fixed-width />
                                        {{ localize("Clear") }}
                                    </GButton>
                                </GButtonGroup>
                            </div>
                        </div>

                        <div v-if="noMoreValidDatasets">
                            <BAlert show variant="warning">
                                {{ localize("No elements left. Would you like to") }}
                                <a class="reset-text" href="javascript:void(0)" role="button" @click="reset">
                                    {{ localize("start over") }}
                                </a>
                                ?
                            </BAlert>
                        </div>

                        <draggable
                            v-model="workingElements"
                            class="collection-elements scroll-container flex-row drop-zone"
                            chosen-class="bg-secondary">
                            <DatasetCollectionElementView
                                v-for="element in workingElements"
                                :key="element.id"
                                :class="{ selected: getSelectedDatasetElements.includes(element.id) }"
                                :element="element"
                                has-actions
                                :selected="getSelectedDatasetElements.includes(element.id)"
                                :show-hid="showHid"
                                @element-is-selected="elementSelected"
                                @element-is-discarded="elementDiscarded"
                                @onRename="(name) => (element.name = name)" />
                        </draggable>
                    </div>

                    <FormSelectMany
                        v-else
                        v-model="inListElements"
                        maintain-selection-order
                        :placeholder="localize('Filter datasets by name')"
                        :options="workingElements.map((e) => ({ label: e.name || '', value: e }))">
                        <template v-slot:column-heading-end>
                            <i style="font-weight: normal">
                                {{ localize("(Click name to edit)") }}
                            </i>
                        </template>
                        <template v-slot:label-area="selectValue">
                            <DatasetCollectionElementView
                                text-only
                                :element="selectionAsHdaSummary(selectValue.option.value)"
                                :hide-extension="!showElementExtension"
                                @onRename="(name) => renameElement(selectValue.option.value, name)" />
                        </template>
                    </FormSelectMany>
                </template>
            </CollectionCreator>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "base.scss";
@import "theme/blue.scss";

.list-collection-creator {
    .footer {
        margin-top: 8px;
    }

    .cancel-create {
        border-color: lightgrey;
    }

    .collection-elements-controls {
        margin-bottom: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        position: relative;

        .center-text {
            position: absolute;
            transform: translateX(-50%);
            left: 50%;
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
        opacity: 1;
        padding: 0 8px 0 8px;
        line-height: 28px;
        cursor: pointer;
        overflow: hidden;
        border: 1px solid lightgrey;
        border-radius: 3px;

        &.with-actions {
            margin: 2px 4px 0px 4px;
            &:hover {
                border-color: black;
            }
        }

        &:last-of-type {
            margin-bottom: 2px;
        }

        &.selected {
            border-color: black;
            background: rgb(118, 119, 131);
            color: white;
            a {
                color: white;
            }
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
