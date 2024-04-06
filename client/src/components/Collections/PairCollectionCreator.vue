<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { computed, onMounted, ref } from "vue";

import type { HDCADetailed, HistoryItemSummary } from "@/api";
import STATES from "@/mvc/dataset/states";
import localize from "@/utils/localization";

import CollectionCreator from "@/components/Collections/common/CollectionCreator.vue";

interface Props {
    initialElements: Array<any>;
    oncancel: () => void;
    oncreate: () => void;
    creationFn: (workingElements: HDCADetailed[], collectionName: string, hideSourceItems: boolean) => any;
    defaultHideSourceItems?: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (event: "clicked-create", workingElements: HDCADetailed[], collectionName: string, hideSourceItems: boolean): void;
}>();

const state = ref("build");
const removeExtensions = ref(true);
const initialSuggestedName = ref("");
const invalidElements = ref<string[]>([]);
const workingElements = ref<HDCADetailed[]>([]);

const allElementsAreInvalid = computed(() => {
    return props.initialElements.length == invalidElements.value.length;
});
const noElementsSelected = computed(() => {
    return props.initialElements.length == 0;
});
const exactlyTwoValidElements = computed(() => {
    return workingElements.value.length == 2;
});
const hideSourceItems = ref(props.defaultHideSourceItems || false);

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

function swapButton() {
    workingElements.value = [workingElements.value[1], workingElements.value[0]] as HDCADetailed[];
}

function clickedCreate(collectionName: string) {
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

function removeExtensionsToggle() {
    removeExtensions.value = !removeExtensions.value;

    initialSuggestedName.value = _guessNameForPair(
        workingElements.value[0] as HDCADetailed,
        workingElements.value[1] as HDCADetailed,
        removeExtensions.value
    );
}

function _guessNameForPair(fwd: HDCADetailed, rev: HDCADetailed, removeExtensions: boolean) {
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

onMounted(() => {
    _elementsSetUp();

    initialSuggestedName.value = _guessNameForPair(
        workingElements.value[0] as HDCADetailed,
        workingElements.value[1] as HDCADetailed,
        removeExtensions.value
    );
});
</script>

<template>
    <div class="pair-collection-creator">
        <div v-if="state == 'error'">
            <BAlert show variant="danger">
                {{ localize("Galaxy could not be reached and may be updating.  Try again in a few minutes.") }}
            </BAlert>
        </div>
        <div v-else>
            <div v-if="noElementsSelected">
                <BAlert show variant="warning" dismissible>
                    {{ localize("No datasets were selected.") }}
                    {{ localize("Exactly two elements needed for the collection. You may need to") }}
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
                        <li v-for="problem in invalidElements" :key="problem">
                            {{ problem }}
                        </li>
                    </ul>
                    {{ localize("Exactly two elements needed for the collection. You may need to") }}
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
            <div v-else-if="!exactlyTwoValidElements">
                <div v-if="invalidElements.length">
                    <BAlert show variant="warning" dismissible>
                        {{ localize("The following selections could not be included due to problems:") }}
                        <ul>
                            <li v-for="problem in invalidElements" :key="problem">
                                {{ problem }}
                            </li>
                        </ul>
                    </BAlert>
                </div>

                <BAlert show variant="warning" dismissible>
                    {{ localize("Two (and only two) elements are needed for the pair. You may need to ") }}
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
                <div v-if="invalidElements.length">
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
                    :oncancel="oncancel"
                    :hide-source-items="hideSourceItems"
                    :suggested-name="initialSuggestedName"
                    @onUpdateHideSourceItems="onUpdateHideSourceItems"
                    @clicked-create="clickedCreate"
                    @remove-extensions-toggle="removeExtensionsToggle">
                    <template v-slot:help-content>
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
                        <div class="collection-elements-controls">
                            <a
                                class="swap"
                                href="javascript:void(0);"
                                title="l('Swap forward and reverse datasets')"
                                @click="swapButton">
                                {{ localize("Swap") }}
                            </a>
                        </div>

                        <div class="collection-elements scroll-container flex-row">
                            <div
                                v-for="(element, index) in workingElements"
                                :key="element.id"
                                class="collection-element">
                                {{ index == 0 ? localize("forward") : localize("reverse") }}: {{ element.name }}
                            </div>
                        </div>
                    </template>
                </CollectionCreator>
            </div>
        </div>
    </div>
</template>

<style lang="scss">
.pair-collection-creator {
    .footer {
        margin-top: 8px;
    }

    .main-help {
        cursor: pointer;
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
    }

    .empty-message {
        margin: 8px;
        color: grey;
        font-style: italic;
        text-align: center;
    }
}
</style>
