<script setup lang="ts">
import { faArrowsAltV } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import type { HDASummary, HistoryItemSummary } from "@/api";
import { Toast } from "@/composables/toast";
import STATES from "@/mvc/dataset/states";
import { useDatatypesMapperStore } from "@/stores/datatypesMapperStore";
import localize from "@/utils/localization";

import type { DatasetPair } from "../History/adapters/buildCollectionModal";

import DatasetCollectionElementView from "./ListDatasetCollectionElementView.vue";
import CollectionCreator from "@/components/Collections/common/CollectionCreator.vue";

const NOT_VALID_ELEMENT_MSG: string = localize("is not a valid element for this collection");

interface SelectedDatasetPair {
    forward: HDASummary | undefined;
    reverse: HDASummary | undefined;
}

interface Props {
    historyId: string;
    initialElements: HistoryItemSummary[];
    defaultHideSourceItems?: boolean;
    fromSelection?: boolean;
    extensions?: string[];
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (event: "clicked-create", selectedPair: DatasetPair, collectionName: string, hideSourceItems: boolean): void;
    (event: "on-cancel"): void;
}>();

const state = ref("build");
const removeExtensions = ref(true);
const initialSuggestedName = ref("");
const invalidElements = ref<string[]>([]);
const workingElements = ref<HDASummary[]>([]);

/** If not `fromSelection`, the manually added elements that will become the pair */
const inListElements = ref<SelectedDatasetPair>({ forward: undefined, reverse: undefined });

const allElementsAreInvalid = computed(() => {
    return props.initialElements.length == invalidElements.value.length;
});
const noElementsSelected = computed(() => {
    return props.initialElements.length == 0;
});
const exactlyTwoValidElements = computed(() => {
    return pairElements.value.forward && pairElements.value.reverse;
});
const hideSourceItems = ref(props.defaultHideSourceItems || false);
const pairElements = computed<SelectedDatasetPair>(() => {
    if (props.fromSelection) {
        return {
            forward: workingElements.value[0],
            reverse: workingElements.value[1],
        };
    } else {
        return inListElements.value;
    }
});

// variables for datatype mapping and then filtering
const datatypesMapperStore = useDatatypesMapperStore();
const datatypesMapper = computed(() => datatypesMapperStore.datatypesMapper);

/** Are we filtering by datatype? */
const filterExtensions = computed(() => !!datatypesMapper.value && !!props.extensions?.length);

watch(
    () => props.initialElements,
    () => {
        // initialize; and then for any new/removed elements, sync working elements
        _elementsSetUp();

        // TODO: fix this, now either of those will almost always be empty
        if (props.fromSelection && !initialSuggestedName.value) {
            initialSuggestedName.value = _guessNameForPair(
                workingElements.value[0] as HDASummary,
                workingElements.value[1] as HDASummary,
                removeExtensions.value
            );
        }
    },
    { immediate: true }
);

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

    // for inListElements, reset their values (in order) to datasets from workingElements
    const inListElementsPrev = inListElements.value;
    inListElements.value = { forward: undefined, reverse: undefined };

    for (const key of ["forward", "reverse"]) {
        const prevElem = inListElementsPrev[key as keyof SelectedDatasetPair];
        if (!prevElem) {
            continue;
        }
        const element = workingElements.value.find(
            (e) => e.id === inListElementsPrev[key as keyof SelectedDatasetPair]?.id
        );
        const problem = _isElementInvalid(prevElem);
        if (element) {
            inListElements.value[key as keyof SelectedDatasetPair] = element;
        } else if (problem) {
            const invalidMsg = `${prevElem.hid}: ${prevElem.name} ${problem} and ${NOT_VALID_ELEMENT_MSG}`;
            invalidElements.value.push(invalidMsg);
            Toast.error(invalidMsg, localize("Invalid element"));
        } else {
            const invalidMsg = `${prevElem.hid}: ${prevElem.name} ${localize("has been removed from the collection")}`;
            invalidElements.value.push(invalidMsg);
            Toast.error(invalidMsg, localize("Invalid element"));
        }
    }

    // TODO: Next thing to add is: If the user adds an uploaded file, that is eventually nuked from workingElements
    //       because it is invalid, Toast an error for that file by keeping track of uploaded ids in a separate list

    _ensureElementIds();
    _validateElements();
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

    // is the element's extension not a subtype of any of the required extensions?
    if (
        filterExtensions.value &&
        element.extension &&
        !datatypesMapper.value?.isSubTypeOfAny(element.extension, props.extensions!)
    ) {
        return localize(`has an invalid extension: ${element.extension}`);
    }
    return null;
}

function getPairElement(key: string) {
    return pairElements.value[key as "forward" | "reverse"];
}

function removeElement(key: string) {
    pairElements.value[key as "forward" | "reverse"] = undefined;
}

function selectElement(element: HDASummary) {
    if (pairElements.value.forward?.id === element.id) {
        pairElements.value.forward = undefined;
    } else if (pairElements.value.reverse?.id === element.id) {
        pairElements.value.reverse = undefined;
    } else if (pairElements.value.forward === undefined) {
        pairElements.value.forward = element;
    } else if (pairElements.value.reverse === undefined) {
        pairElements.value.reverse = element;
    }
}

function swapButton() {
    if (!exactlyTwoValidElements.value) {
        return;
    }
    if (props.fromSelection) {
        workingElements.value = [workingElements.value[1], workingElements.value[0]] as HDASummary[];
    } else {
        inListElements.value = {
            forward: inListElements.value.reverse,
            reverse: inListElements.value.forward,
        };
    }
}

function addUploadedFiles(files: HDASummary[]) {
    // Any added files are added to workingElements in _elementsSetUp
    // The user will have to manually select the files to add them to the pair

    // Check for validity of uploads
    files.forEach((file) => {
        const problem = _isElementInvalid(file);
        if (problem) {
            const invalidMsg = `${file.hid}: ${file.name} ${problem} and ${NOT_VALID_ELEMENT_MSG}`;
            invalidElements.value.push(invalidMsg);
            Toast.error(invalidMsg, localize("Uploaded item invalid for pair"));
        }
    });
}

function clickedCreate(collectionName: string) {
    if (state.value !== "error" && exactlyTwoValidElements.value) {
        const returnedPair = {
            forward: pairElements.value.forward as HDASummary,
            reverse: pairElements.value.reverse as HDASummary,
            name: collectionName,
        };
        emit("clicked-create", returnedPair, collectionName, hideSourceItems.value);
    }
}

function removeExtensionsToggle() {
    removeExtensions.value = !removeExtensions.value;

    initialSuggestedName.value = _guessNameForPair(
        workingElements.value[0] as HDASummary,
        workingElements.value[1] as HDASummary,
        removeExtensions.value
    );
}

function _guessNameForPair(fwd: HDASummary, rev: HDASummary, removeExtensions: boolean) {
    removeExtensions = removeExtensions ? removeExtensions : removeExtensions;

    var fwdName = fwd.name ?? "";
    var revName = rev.name ?? "";
    var lcs = _naiveStartingAndEndingLCS(fwdName, revName);

    /** remove url prefix if files were uploaded by url */
    var lastDotIndex = lcs.lastIndexOf(".");
    var lastSlashIndex = lcs.lastIndexOf("/");
    var extension = lcs.slice(lastDotIndex, lcs.length);

    if (lastSlashIndex > 0) {
        var urlprefix = lcs.slice(0, lastSlashIndex + 1);

        lcs = lcs.replace(urlprefix, "");
        fwdName = fwdName.replace(extension, "");
        revName = revName.replace(extension, "");
    }

    if (removeExtensions) {
        if (lastDotIndex > 0) {
            lcs = lcs.replace(extension, "");
            fwdName = fwdName.replace(extension, "");
            revName = revName.replace(extension, "");
        }
    }

    return lcs || `${fwdName} & ${revName}`;
}

function onUpdateHideSourceItems(newHideSourceItems: boolean) {
    hideSourceItems.value = newHideSourceItems;
}

function _naiveStartingAndEndingLCS(s1: string, s2: string) {
    var i = 0;
    var j = 0;
    var fwdLCS = "";
    var revLCS = "";

    while (i < s1.length && i < s2.length) {
        if (s1[i] !== s2[i]) {
            break;
        }

        fwdLCS += s1[i];
        i += 1;
    }

    if (i === s1.length) {
        return s1;
    }

    if (i === s2.length) {
        return s2;
    }

    i = s1.length - 1;
    j = s2.length - 1;

    while (i >= 0 && j >= 0) {
        if (s1[i] !== s2[j]) {
            break;
        }

        revLCS = [s1[i], revLCS].join("");
        i -= 1;
        j -= 1;
    }

    return fwdLCS + revLCS;
}
</script>

<template>
    <div class="pair-collection-creator">
        <div v-if="state == 'error'">
            <BAlert show variant="danger">
                {{ localize("Galaxy could not be reached and may be updating.  Try again in a few minutes.") }}
            </BAlert>
        </div>
        <div v-else>
            <div v-if="fromSelection && invalidElements.length">
                <BAlert show variant="warning" dismissible>
                    {{ localize("The following selections could not be included due to problems:") }}
                    <ul>
                        <li v-for="problem in invalidElements" :key="problem">
                            {{ problem }}
                        </li>
                    </ul>
                </BAlert>
            </div>
            <div v-if="!exactlyTwoValidElements">
                <BAlert show variant="warning" dismissible>
                    {{ localize("Exactly two elements are needed for the pair.") }}
                    <span v-if="fromSelection">
                        <a class="cancel-text" href="javascript:void(0)" role="button" @click="emit('on-cancel')">
                            {{ localize("Cancel") }}
                        </a>
                        {{ localize("and reselect new elements.") }}
                    </span>
                </BAlert>

                <div v-if="fromSelection" class="float-left">
                    <button class="cancel-create btn" tabindex="-1" @click="emit('on-cancel')">
                        {{ localize("Cancel") }}
                    </button>
                </div>
            </div>

            <CollectionCreator
                :oncancel="() => emit('on-cancel')"
                :history-id="props.historyId"
                :hide-source-items="hideSourceItems"
                :suggested-name="initialSuggestedName"
                :extensions="props.extensions"
                :extensions-toggle="removeExtensions"
                :no-items="props.initialElements.length == 0 && !props.fromSelection"
                @add-uploaded-files="addUploadedFiles"
                @onUpdateHideSourceItems="onUpdateHideSourceItems"
                @clicked-create="clickedCreate"
                @remove-extensions-toggle="removeExtensionsToggle">
                <template v-slot:help-content>
                    <!-- TODO: Update help content for case where `fromSelection` is false -->
                    <p>
                        {{
                            localize(
                                [
                                    "Pair collections are permanent collections containing two datasets: one forward and one reverse. ",
                                    "Often these are forward and reverse reads. The pair collections can be passed to tools and workflows in ",
                                    "order to have analyses done on both datasets. This interface allows you to create a pair, name it, and ",
                                    "swap which is forward and which reverse.",
                                ].join("")
                            )
                        }}
                    </p>

                    <ul>
                        <li>
                            {{ localize("Click the ") }}
                            <i data-target=".swap">
                                {{ localize("Swap") }}
                            </i>
                            {{
                                localize(
                                    "link to make your forward dataset the reverse and the reverse dataset forward"
                                )
                            }}
                        </li>

                        <li>
                            {{ localize("Click the ") }}
                            <i data-target=".cancel-create">
                                {{ localize("Cancel") }}
                            </i>
                            {{ localize("button to exit the interface.") }}
                        </li>
                    </ul>

                    <br />

                    <p>
                        {{ localize("Once your collection is complete, enter a ") }}
                        <i data-target=".collection-name"> {{ localize("name") }}</i>
                        {{ localize("and click ") }}
                        <i data-target=".create-collection">
                            {{ localize("Create list") }}
                        </i>
                        {{ localize(".") }}
                    </p>
                </template>

                <template v-slot:middle-content>
                    <div v-if="noElementsSelected">
                        <BAlert show variant="warning" dismissible>
                            {{ localize("No datasets were selected.") }}
                            {{ localize("Exactly two elements needed for the collection. You may need to") }}
                            <a class="cancel-text" href="javascript:void(0)" role="button" @click="emit('on-cancel')">
                                {{ localize("cancel") }}
                            </a>
                            {{ localize("and reselect new elements.") }}
                        </BAlert>

                        <div class="float-left">
                            <button class="cancel-create btn" tabindex="-1" @click="emit('on-cancel')">
                                {{ localize("Cancel") }}
                            </button>
                        </div>
                    </div>
                    <div v-else-if="allElementsAreInvalid">
                        <BAlert v-if="!fromSelection" show variant="warning">
                            {{
                                localize(
                                    "No elements in your history are valid for this pair. You may need to switch to a different history."
                                )
                            }}
                            <span v-if="extensions?.length">
                                {{ localize("The following extensions are required for this pair: ") }}
                                <ul>
                                    <li v-for="extension in extensions" :key="extension">
                                        {{ extension }}
                                    </li>
                                </ul>
                            </span>
                        </BAlert>
                        <BAlert v-else show variant="warning" dismissible>
                            {{ localize("The following selections could not be included due to problems:") }}
                            <ul>
                                <li v-for="problem in invalidElements" :key="problem">
                                    {{ problem }}
                                </li>
                            </ul>
                            {{ localize("Exactly two elements needed for the collection. You may need to") }}
                            <a class="cancel-text" href="javascript:void(0)" role="button" @click="emit('on-cancel')">
                                {{ localize("cancel") }}
                            </a>
                            {{ localize("and reselect new elements.") }}
                        </BAlert>

                        <div class="float-left">
                            <button class="cancel-create btn" tabindex="-1" @click="emit('on-cancel')">
                                {{ localize("Cancel") }}
                            </button>
                        </div>
                    </div>
                    <div v-else>
                        <div class="collection-elements-controls">
                            <BButton
                                class="swap"
                                size="sm"
                                :disabled="!exactlyTwoValidElements"
                                :title="localize('Swap forward and reverse datasets')"
                                @click="swapButton">
                                <FontAwesomeIcon :icon="faArrowsAltV" fixed-width />
                                {{ localize("Swap") }}
                            </BButton>
                        </div>

                        <div class="collection-elements flex-row mb-3">
                            <div v-for="dataset in ['forward', 'reverse']" :key="dataset">
                                {{ localize(dataset) }}:
                                <DatasetCollectionElementView
                                    v-if="getPairElement(dataset)"
                                    :key="getPairElement(dataset)?.id"
                                    :element="getPairElement(dataset)"
                                    has-actions
                                    @element-is-discarded="removeElement(dataset)" />
                                <div v-else class="collection-element alert-info">
                                    <i>{{ localize("No dataset selected") }}</i>
                                </div>
                            </div>
                        </div>

                        <div v-if="!fromSelection">
                            {{ localize("Manually select a forward and reverse dataset to create a pair collection:") }}
                            <div class="collection-elements">
                                <DatasetCollectionElementView
                                    v-for="element in workingElements"
                                    :key="element.id"
                                    :class="{
                                        selected: [pairElements.forward, pairElements.reverse].includes(element),
                                    }"
                                    :element="element"
                                    not-editable
                                    :selected="[pairElements.forward, pairElements.reverse].includes(element)"
                                    @element-is-selected="selectElement"
                                    @onRename="(name) => (element.name = name)" />
                            </div>
                        </div>
                    </div>
                </template>
            </CollectionCreator>
        </div>
    </div>
</template>

<style lang="scss">
.pair-collection-creator {
    .footer {
        margin-top: 8px;
    }

    .collection-elements-controls {
        margin-bottom: 8px;
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

        button {
            margin-top: 3px;
        }

        .identifier {
            &:after {
                content: ":";
                margin-right: 6px;
            }
        }

        .name {
            &:hover {
                text-decoration: none;
            }
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
