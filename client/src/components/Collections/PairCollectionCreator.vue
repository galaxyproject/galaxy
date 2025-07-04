<script setup lang="ts">
import { faArrowsAltV } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import type { CollectionElementIdentifiers, CreateNewCollectionPayload, HDASummary, HistoryItemSummary } from "@/api";
import { useAnimationFrameResizeObserver } from "@/composables/sensors/animationFrameResizeObserver";
import { useAnimationFrameScroll } from "@/composables/sensors/animationFrameScroll";
import { Toast } from "@/composables/toast";
import localize from "@/utils/localization";

import { type Mode, useCollectionCreator } from "./common/useCollectionCreator";
import { guessNameForPair } from "./pairing";

import GButton from "../BaseComponents/GButton.vue";
import DelayedInput from "../Common/DelayedInput.vue";
import HelpText from "../Help/HelpText.vue";
import FixedIdentifierDatasetCollectionElementView from "./FixedIdentifierDatasetCollectionElementView.vue";
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
    suggestedName?: string;
    fromSelection?: boolean;
    extensions?: string[];
    mode: Mode;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "name", value: string): void;
    (e: "input-valid", value: boolean): void;
    (e: "on-create", options: CreateNewCollectionPayload): void;
    (e: "on-cancel"): void;
}>();

const state = ref("build");
const initialSuggestedName = ref(props.suggestedName);
const invalidElements = ref<string[]>([]);
const workingElements = ref<HDASummary[]>([]);
const filterText = ref("");

const filteredElements = computed(() => {
    return workingElements.value.filter((element) => {
        return `${element.hid}: ${element.name}`.toLowerCase().includes(filterText.value.toLowerCase());
    });
});

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
const pairHasMixedExtensions = computed(() => {
    return (
        pairElements.value.forward?.extension &&
        pairElements.value.reverse?.extension &&
        pairElements.value.forward.extension !== pairElements.value.reverse.extension
    );
});

const {
    collectionName,
    removeExtensions,
    hideSourceItems,
    onUpdateHideSourceItems,
    isElementInvalid,
    onCollectionCreate,
    showButtonsForModal,
    onUpdateCollectionName,
} = useCollectionCreator(props, emit);

// check if we have scrolled to the top or bottom of the scrollable div
const scrollableDiv = ref<HTMLDivElement | null>(null);
const { arrived } = useAnimationFrameScroll(scrollableDiv);
const isScrollable = ref(false);
useAnimationFrameResizeObserver(scrollableDiv, ({ clientSize, scrollSize }) => {
    isScrollable.value = scrollSize.height >= clientSize.height + 1;
});
const scrolledTop = computed(() => !isScrollable.value || arrived.top);
const scrolledBottom = computed(() => !isScrollable.value || arrived.bottom);

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
        const matchingElem = workingElements.value.find(
            (e) => e.id === inListElementsPrev[key as keyof SelectedDatasetPair]?.id
        );
        if (matchingElem) {
            const problem = isElementInvalid(matchingElem);
            if (problem) {
                const invalidMsg = `${prevElem.hid}: ${prevElem.name} ${problem} and ${NOT_VALID_ELEMENT_MSG}`;
                Toast.error(invalidMsg, localize("Invalid element"));
            } else {
                inListElements.value[key as keyof SelectedDatasetPair] = matchingElem;
            }
        } else {
            const invalidMsg = `${prevElem.hid}: ${prevElem.name} ${localize("has been removed from the collection")}`;
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
        const problem = isElementInvalid(element);

        if (problem) {
            invalidElements.value.push(element.name + "  " + problem);
        }

        return !problem;
    });

    return workingElements.value;
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

    let alreadyPopulated = false;

    // Check for validity of uploads, and add them to the pair if space is available
    files.forEach((file) => {
        const element = workingElements.value.find((e) => e.id === file.id);
        if (element) {
            const problem = isElementInvalid(file);
            if (problem) {
                const invalidMsg = `${element.hid}: ${element.name} ${problem} and ${NOT_VALID_ELEMENT_MSG}`;
                invalidElements.value.push(invalidMsg);
                Toast.error(invalidMsg, localize("Uploaded item invalid for pair"));
            } else if (!props.fromSelection) {
                if (inListElements.value.forward === undefined) {
                    inListElements.value.forward = element;
                } else if (inListElements.value.reverse === undefined) {
                    inListElements.value.reverse = element;
                } else if (!alreadyPopulated) {
                    alreadyPopulated = true;
                }
            }
        }
    });
    if (alreadyPopulated && files.length > 0) {
        Toast.info(
            localize("Forward and reverse datasets already selected. Uploaded files are available for replacement."),
            localize("Uploads Available for Replacement")
        );
    }
}

function attemptCreate() {
    if (state.value !== "error" && exactlyTwoValidElements.value) {
        const forward = pairElements.value.forward as HDASummary;
        const reverse = pairElements.value.reverse as HDASummary;
        const returnedElems = [
            { name: "forward", src: "src" in forward ? forward.src : "hda", id: forward.id },
            { name: "reverse", src: "src" in reverse ? reverse.src : "hda", id: reverse.id },
        ] as CollectionElementIdentifiers;
        onCollectionCreate("paired", returnedElems);
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
    return guessNameForPair(fwd, rev, "", "", removeExtensions);
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

            <CollectionCreator
                :oncancel="() => emit('on-cancel')"
                :history-id="props.historyId"
                :hide-source-items="hideSourceItems"
                :suggested-name="initialSuggestedName"
                :extensions="props.extensions"
                :extensions-toggle="removeExtensions"
                collection-type="paired"
                :no-items="props.initialElements.length == 0 && !props.fromSelection"
                :show-upload="!fromSelection"
                :show-buttons="showButtonsForModal"
                :collection-name="collectionName"
                :mode="mode"
                @on-update-collection-name="onUpdateCollectionName"
                @add-uploaded-files="addUploadedFiles"
                @onUpdateHideSourceItems="onUpdateHideSourceItems"
                @clicked-create="attemptCreate"
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
                            {{ localize("Create dataset pair") }}
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
                            {{ localize("and reselect new elements, or upload datasets.") }}
                        </BAlert>
                    </div>
                    <div v-else-if="allElementsAreInvalid">
                        <BAlert v-if="!fromSelection" show variant="warning">
                            {{
                                localize(
                                    "No elements in your history are valid for this pair. \
                                    You may need to switch to a different history or upload valid datasets."
                                )
                            }}
                            <div v-if="extensions?.length">
                                {{ localize("The following formats are required for this pair: ") }}
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
                                <li v-for="problem in invalidElements" :key="problem">
                                    {{ problem }}
                                </li>
                            </ul>
                            {{ localize("Exactly two elements needed for the collection. You may need to") }}
                            <a class="cancel-text" href="javascript:void(0)" role="button" @click="emit('on-cancel')">
                                {{ localize("cancel") }}
                            </a>
                            {{ localize("and reselect new elements, or upload datasets.") }}
                        </BAlert>
                    </div>
                    <div v-else>
                        <div class="collection-elements-controls flex-gapx-1">
                            <div>
                                <GButton
                                    class="swap"
                                    size="small"
                                    :disabled="!exactlyTwoValidElements"
                                    :title="localize('Swap forward and reverse datasets')"
                                    @click="swapButton">
                                    <FontAwesomeIcon :icon="faArrowsAltV" fixed-width />
                                    {{ localize("Swap") }}
                                </GButton>
                            </div>
                            <div class="flex-grow-1">
                                <BAlert v-if="!exactlyTwoValidElements" show variant="warning">
                                    {{ localize("Exactly two elements are needed for the pair.") }}
                                    <span v-if="fromSelection">
                                        <a
                                            class="cancel-text"
                                            href="javascript:void(0)"
                                            role="button"
                                            @click="emit('on-cancel')">
                                            {{ localize("Cancel") }}
                                        </a>
                                        {{ localize("and reselect new elements.") }}
                                    </span>
                                </BAlert>
                                <BAlert v-else-if="pairHasMixedExtensions" show variant="warning">
                                    {{ localize("The selected datasets have mixed formats.") }}
                                    {{ localize("You can still create the pair but generally") }}
                                    {{ localize("dataset pairs should contain datasets of the same type.") }}
                                    <HelpText
                                        uri="galaxy.collections.collectionBuilder.whyHomogenousCollections"
                                        :text="localize('Why?')" />
                                </BAlert>
                                <BAlert v-else show variant="success">
                                    {{ localize("The Dataset Pair is ready to be created.") }}
                                    {{ localize("Provide a name and click the button below to create the pair.") }}
                                </BAlert>
                            </div>
                        </div>

                        <div class="flex-row mb-3">
                            <div v-for="dataset in ['forward', 'reverse']" :key="dataset">
                                {{ localize(dataset) }}:
                                <FixedIdentifierDatasetCollectionElementView
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
                            <DelayedInput v-model="filterText" placeholder="search datasets" :delay="800" />
                            <strong>
                                {{
                                    localize("Manually select a forward and reverse dataset to create a dataset pair:")
                                }}
                            </strong>
                            <div
                                v-if="filteredElements.length"
                                class="scroll-list-container"
                                :class="{ 'scrolled-top': scrolledTop, 'scrolled-bottom': scrolledBottom }">
                                <div ref="scrollableDiv" class="collection-elements">
                                    <DatasetCollectionElementView
                                        v-for="element in filteredElements"
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
                            <BAlert v-else show variant="info">
                                {{ localize(`No datasets found${filterText ? " matching '" + filterText + "'" : ""}`) }}
                            </BAlert>
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
        display: flex;
        justify-content: space-between;
        align-items: center;

        .alert {
            padding: 0.25rem 0.5rem;
            margin: 0;
            text-align: center;
        }
    }

    .collection-elements {
        max-height: 30vh;
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
