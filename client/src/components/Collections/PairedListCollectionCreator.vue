<script setup lang="ts">
import {
    faAngleDown,
    faAngleUp,
    faExclamationCircle,
    faLink,
    faTimes,
    faUnlink,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BButtonGroup, BCard, BCardBody, BCardHeader } from "bootstrap-vue";
import { computed, ref, watch } from "vue";
import draggable from "vuedraggable";

import type { HDASummary, HistoryItemSummary } from "@/api";
import { Toast } from "@/composables/toast";
import STATES from "@/mvc/dataset/states";
import { useDatatypesMapperStore } from "@/stores/datatypesMapperStore";
// import levenshteinDistance from '@/utils/levenshtein';
import localize from "@/utils/localization";
import { naturalSort } from "@/utils/naturalSort";

import type { DatasetPair } from "../History/adapters/buildCollectionModal";

import Heading from "../Common/Heading.vue";
import PairedElementView from "./PairedElementView.vue";
import UnpairedDatasetElementView from "./UnpairedDatasetElementView.vue";
import CollectionCreator from "@/components/Collections/common/CollectionCreator.vue";

const NOT_VALID_ELEMENT_MSG: string = localize("is not a valid element for this collection");
const COMMON_FILTERS = {
    illumina: ["_1", "_2"],
    Rs: ["_R1", "_R2"],
    dot12s: [".1.fastq", ".2.fastq"],
};
const DEFAULT_FILTER: keyof typeof COMMON_FILTERS = "illumina";
const MATCH_PERCENTAGE = 0.99;

// Titles and help text
const CHOOSE_FILTER_TITLE = localize("Choose from common filters");
const FILTER_TEXT_PLACEHOLDER = localize("Filter text");
const FILTER_TEXT_TITLE = localize("Use this box to filter elements, using simple matching or regular expressions.");
const ERROR_TEXT = localize("There was a problem creating the collection.");
const INVALID_HEADER = localize("The following selections could not be included due to problems:");
const ALL_INVALID_ELEMENTS_PART_ONE = localize("At least two elements are needed for the collection. You may need to");
const CANCEL_TEXT = localize("Cancel");

interface Props {
    historyId: string;
    initialElements: HistoryItemSummary[];
    defaultHideSourceItems?: boolean;
    fromSelection?: boolean;
    extensions?: string[];
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "clicked-create", workingElements: DatasetPair[], collectionName: string, hideSourceItems: boolean): void;
    (e: "on-cancel"): void;
}>();

// Titles and help text computed
const noElementsHeader = props.fromSelection ? localize("No elements selected") : localize("No elements available");
const allInvalidElementsPartTwo = props.fromSelection
    ? localize("and reselect new elements.")
    : localize("and change your current history or upload valid datasets for this collection.");

// Flags
const state = ref<"build" | "error" | "duplicates">("build");
const hideSourceItems = ref(props.defaultHideSourceItems || false);
const autoPairsPossible = ref(true);
const twoPassAutoPairing = ref(true);
const removeExtensions = ref(true);
const firstAutoPairDone = ref(false);
const showPairingSection = ref(true);

// Elements
const workingElements = ref<HDASummary[]>([]);
const invalidElements = ref<string[]>([]);
const generatedPairs = ref<DatasetPair[]>([]);
const selectedForwardElement = ref<HDASummary | null>(null);
const selectedReverseElement = ref<HDASummary | null>(null);

// Filters
const forwardFilter = ref(COMMON_FILTERS[DEFAULT_FILTER][0] || "");
const reverseFilter = ref(COMMON_FILTERS[DEFAULT_FILTER][1] || "");
const hasFilter = computed(() => forwardFilter.value || reverseFilter.value);

// Autopairing
const strategy = ref(autoPairLCS);
const duplicatePairNames = ref<string[]>([]);

const forwardElements = computed<HDASummary[]>(() => {
    return filterElements(workingElements.value, forwardFilter.value);
});
const reverseElements = computed<HDASummary[]>(() => {
    return filterElements(workingElements.value, reverseFilter.value);
});
const pairableElements = computed(() => {
    const pairable: DatasetPair[] = [];
    forwardElements.value.forEach((forwardElement, index) => {
        const reverseElement = reverseElements.value[index];
        if (!!reverseElement && !!forwardElement && forwardElement.id != reverseElement.id) {
            pairable.push({
                forward: forwardElement,
                reverse: reverseElement,
                name: _guessNameForPair(forwardElement, reverseElement),
            });
        }
    });
    return pairable;
});
const autoPairButton = computed(() => {
    let variant;
    let icon;
    let text;
    if (!firstAutoPairDone.value && pairableElements.value.length > 0) {
        variant = "primary";
        icon = faExclamationCircle;
        text = localize("Click to auto-pair datasets based on the current filters");
    } else if (pairableElements.value.length > 0) {
        variant = "secondary";
        icon = faLink;
        text = localize("Auto-pair possible based on current filters");
    } else {
        variant = "secondary";
        icon = faLink;
        text = localize("Click to attempt auto-pairing datasets");
    }
    return { variant, icon, text };
});
const numOfUnpairedForwardElements = computed(() => {
    return forwardElements.value.length;
});
const numOfFilteredOutForwardElements = computed(() => {
    return workingElements.value.length - numOfUnpairedForwardElements.value;
});
const numOfUnpairedReverseElements = computed(() => {
    return reverseElements.value.length;
});
const numOfFilteredOutReverseElements = computed(() => {
    return workingElements.value.length - numOfUnpairedReverseElements.value;
});
const numOfPairs = computed(() => {
    return generatedPairs.value.length;
});
const returnInvalidElementsLength = computed(() => {
    return invalidElements.value.length > 0;
});
const returnInvalidElements = computed(() => {
    return invalidElements.value;
});
const allElementsAreInvalid = computed(() => {
    return props.initialElements.length === invalidElements.value.length;
});
const noElementsSelected = computed(() => {
    return props.initialElements.length === 0;
});
const tooFewElementsSelected = computed(() => {
    return workingElements.value.length < 2 && generatedPairs.value.length === 0;
});
// TODO: Include in the template
// const showDuplicateError = computed(() => {
//     return duplicatePairNames.value.length > 0;
// });

const noUnpairedElementsDisplayed = computed(() => {
    return numOfUnpairedForwardElements.value + numOfUnpairedReverseElements.value === 0;
});

// variables for datatype mapping and then filtering
const datatypesMapperStore = useDatatypesMapperStore();
const datatypesMapper = computed(() => datatypesMapperStore.datatypesMapper);

/** Are we filtering by datatype? */
const filterExtensions = computed(() => !!datatypesMapper.value && !!props.extensions?.length);

function removeExtensionsToggle() {
    removeExtensions.value = !removeExtensions.value;
    generatedPairs.value.forEach((pair, index) => {
        pair.name = _guessNameForPair(pair.forward, pair.reverse, removeExtensions.value);
    });
}

watch(
    () => props.initialElements,
    () => {
        // initialize; and then for any new/removed elements, sync working elements
        _elementsSetUp();
    },
    { immediate: true }
);

/** Set up main data */
function _elementsSetUp() {
    // a list of invalid elements and the reasons they aren't valid
    invalidElements.value = [];
    //TODO: handle fundamental problem of syncing DOM, views, and list here
    // data for list in progress
    workingElements.value = [];
    //TODO: this should maybe be in it's own method as it will get called everytime selected array has two elements and dumps again.
    // selectedDatasetElems = [];
    initialFiltersSet();
    // copy initial list, sort, // TODO: add ids if needed
    // copy initial list, sort, add ids if needed
    workingElements.value = JSON.parse(JSON.stringify(props.initialElements.slice(0)));

    // TODO: Here, we do what we do in other 2 creators; we check the already built pairs
    //       and sync them with the workingElements, ensuring that there aren't any elements
    //       in built pairs that no longer exist in workingElements

    // _ensureElementIds();
    _validateElements();
    _sortInitialList();
    // attempt to autopair
    if (props.fromSelection) {
        autoPair();
    }
}

function initialFiltersSet() {
    let illumina = 0;
    let dot12s = 0;
    let Rs = 0;
    //should we limit the forEach? What if there are 1000s of elements?
    props.initialElements.forEach((element) => {
        if (element.name?.includes(".1.fastq") || element.name?.includes(".2.fastq")) {
            dot12s++;
        } else if (element.name?.includes("_R1") || element.name?.includes("_R2")) {
            Rs++;
        } else if (element.name?.includes("_1") || element.name?.includes("_2")) {
            illumina++;
        }
    });

    if (illumina > dot12s && illumina > Rs) {
        changeFilters("illumina");
    } else if (dot12s > illumina && dot12s > Rs) {
        changeFilters("dot12s");
    } else if (Rs > illumina && Rs > dot12s) {
        changeFilters("Rs");
    } else {
        changeFilters("illumina");
    }
}

// TODO: Don't know if this is really necessary
// function _ensureElementIds() {
//     workingElements.value.forEach((element) => {
//         if (!Object.prototype.hasOwnProperty.call(element, "id")) {
//             console.warn("Element missing id", element);
//         }
//     });

//     return workingElements.value;
// }

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

function _sortInitialList() {
    workingElements.value.sort((a, b) => naturalSort(a.name || "", b.name || ""));
}

function filterElements(elements: HDASummary[], filterText: string) {
    return elements.filter((e) => filterElement(e, filterText));
}

function filterElement(element: HDASummary, filterText: string) {
    return filterText == "" || new RegExp(filterText).test(element.name || "");
}

function forwardElementSelected(e: HDASummary) {
    if (selectedForwardElement.value == null || selectedForwardElement.value.id != e.id) {
        selectedForwardElement.value = e;
    } else {
        selectedForwardElement.value = null;
    }
    if (
        selectedForwardElement.value &&
        selectedReverseElement.value &&
        selectedReverseElement.value != selectedForwardElement.value
    ) {
        _pair(selectedForwardElement.value, selectedReverseElement.value);
    }
}

function reverseElementSelected(e: HDASummary) {
    if (selectedReverseElement.value == null || selectedReverseElement.value.id != e.id) {
        selectedReverseElement.value = e;
    } else {
        selectedReverseElement.value = null;
    }
    if (
        selectedForwardElement.value &&
        selectedReverseElement.value &&
        selectedReverseElement.value != selectedForwardElement.value
    ) {
        _pair(selectedForwardElement.value, selectedReverseElement.value);
    }
}

// ------------------------------------------------------- pairing / unpairing
/**
 * Create a pair from fwd and rev, removing them from unpaired,
 * and placing the new pair in paired
 */
function _pair(fwd: HDASummary, rev: HDASummary, options: { name?: string } = {}) {
    const pair = _createPair(fwd, rev, options.name);
    generatedPairs.value.push(pair);
    removePairFromUnpaired(fwd, rev);
    // if (!options.silent) {
    //     emit("pair:new", pair);
    // }
    return pair;
}

function removePairFromUnpaired(fwd: HDASummary, rev: HDASummary) {
    workingElements.value.splice(workingElements.value.indexOf(rev), 1);
    workingElements.value.splice(workingElements.value.indexOf(fwd), 1);
    selectedForwardElement.value = null;
    selectedReverseElement.value = null;
}

/**
 * Create a pair Object from fwd and rev, adding the name attribute
 * (will guess if not given)
 */
function _createPair(fwd: HDASummary, rev: HDASummary, name?: string) {
    // ensure existance and don't pair something with itself
    if (!(fwd && rev) || fwd === rev) {
        throw new Error(`Bad pairing: ${[JSON.stringify(fwd), JSON.stringify(rev)]}`);
    }
    name = name || _guessNameForPair(fwd, rev);
    return { forward: fwd, name: name, reverse: rev };
}

/** Try to find a good pair name for the given fwd and rev datasets */
function _guessNameForPair(fwd: HDASummary, rev: HDASummary, willRemoveExtensions?: boolean) {
    willRemoveExtensions = willRemoveExtensions ? willRemoveExtensions : removeExtensions.value;
    let fwdName = fwd.name;
    let revName = rev.name;
    const fwdNameFilter = fwdName?.replace(new RegExp(forwardFilter.value || ""), "");
    const revNameFilter = revName?.replace(new RegExp(reverseFilter.value || ""), "");
    if (!fwdNameFilter || !revNameFilter || !fwdName || !revName) {
        return `${fwdName} & ${revName}`;
    }
    let lcs = _naiveStartingAndEndingLCS(fwdNameFilter, revNameFilter);
    // remove url prefix if files were uploaded by url
    const lastSlashIndex = lcs.lastIndexOf("/");
    if (lastSlashIndex > 0) {
        const urlprefix = lcs.slice(0, lastSlashIndex + 1);
        lcs = lcs.replace(urlprefix, "");
    }

    if (willRemoveExtensions) {
        const lastDotIndex = lcs.lastIndexOf(".");
        if (lastDotIndex > 0) {
            const extension = lcs.slice(lastDotIndex, lcs.length);
            lcs = lcs.replace(extension, "");
            fwdName = fwdName.replace(extension, "");
            revName = revName.replace(extension, "");
        }
    }
    if (lcs.endsWith(".") || lcs.endsWith("_")) {
        lcs = lcs.substring(0, lcs.length - 1);
    }
    return lcs || `${fwdName} & ${revName}`;
}

function clickAutopair() {
    // Unselect any selected elements
    selectedForwardElement.value = null;
    selectedReverseElement.value = null;
    autoPair();

    workingElements.value = workingElements.value.filter((e) => {
        return !generatedPairs.value.some((pair) => pair.forward.id === e.id || pair.reverse.id === e.id);
    });
}

function clickUnpair(pair: DatasetPair) {
    return _unpair(pair);
}

function clickClearFilters() {
    forwardFilter.value = "";
    reverseFilter.value = "";
}

function splitByFilter() {
    const filters = [new RegExp(forwardFilter.value), new RegExp(reverseFilter.value)];
    const split: [HDASummary[], HDASummary[]] = [[], []];
    workingElements.value.forEach((e) => {
        filters.forEach((filter, i) => {
            if (e.name && filter.test(e.name)) {
                split[i]?.push(e);
            }
        });
    });
    return split;
}
// ===========================================================================

// -------------------------------------------------------------- auto pairing
/** Autopair by exact match */
function autoPairSimple(params: { listA: HDASummary[]; listB: HDASummary[] }) {
    return autoPairFnBuilder({
        match: (params) => {
            params = params || {};
            if (params.matchTo === params.possible) {
                return {
                    index: params.index,
                    score: 1.0,
                };
            }
            return params.bestMatch;
        },
        scoreThreshold: 0.6,
    })(params);
}

// TODO: Currently unused?
/** Autopair by levenstein distance */
// function autoPairLevenshtein(params: { listA: HDASummary[]; listB: HDASummary[] }) {
//     return autoPairFnBuilder({
//         match: (params) => {
//             params = params || {};
//             const distance = levenshteinDistance(params.matchTo, params.possible);
//             const score = 1.0 - distance / Math.max(params.matchTo.length, params.possible.length);
//             if (score > params.bestMatch.score) {
//                 return {
//                     index: params.index,
//                     score: score,
//                 };
//             }
//             return params.bestMatch;
//         },
//         scoreThreshold: MATCH_PERCENTAGE,
//     })(params);
// }

/** Autopair by longest common substrings scoring */
function autoPairLCS(params: { listA: HDASummary[]; listB: HDASummary[] }) {
    return autoPairFnBuilder({
        match: (params) => {
            params = params || {};
            const match = _naiveStartingAndEndingLCS(params.matchTo, params.possible).length;
            const score = match / Math.max(params.matchTo.length, params.possible.length);
            if (score > params.bestMatch.score) {
                return {
                    index: params.index,
                    score: score,
                };
            }
            return params.bestMatch;
        },
        scoreThreshold: MATCH_PERCENTAGE,
    })(params);
}

/**
 * Two passes to automatically create pairs:
 * use both simpleAutoPair, then the fn mentioned in strategy
 */
function autoPair(localStrategy?: (params: { listA: HDASummary[]; listB: HDASummary[] }) => DatasetPair[]) {
    let split = splitByFilter();
    let paired: DatasetPair[] = [];
    if (twoPassAutoPairing.value) {
        const simplePaired = autoPairSimple({
            listA: split[0],
            listB: split[1],
        });
        paired = simplePaired ? simplePaired : paired;
        split = splitByFilter();
    }

    // then try the remainder with something less strict
    localStrategy = localStrategy || strategy.value;
    split = splitByFilter();
    const pairedStrategy = localStrategy({
        listA: split[0],
        listB: split[1],
    });
    paired = pairedStrategy ? paired.concat(pairedStrategy) : paired;
    autoPairsPossible.value = paired.length > 0;
    firstAutoPairDone.value = true;
    return paired;
}

/** Add a dataset to the unpaired list in it's proper order */
function _addToUnpaired(dataset: HDASummary) {
    /** Currently, unpaired is natural sorted by name, use binary search to find insertion point */
    function binSearchSortedIndex(low: number, hi: number) {
        if (low === hi) {
            return low;
        }

        let mid = Math.floor((hi - low) / 2) + low;

        const elementAtPoint = workingElements.value[mid];

        const compared = naturalSort(dataset.name || "", elementAtPoint?.name || "");

        if (compared < 0) {
            return binSearchSortedIndex(low, mid);
        } else if (compared > 0) {
            return binSearchSortedIndex(mid + 1, hi);
        } else if (!elementAtPoint) {
            return mid;
        }
        // walk the equal to find the last // TODO: Investigate this, is this correct?
        if (elementAtPoint?.name === dataset.name) {
            mid++;
        }
        return mid;
    }

    workingElements.value.splice(binSearchSortedIndex(0, workingElements.value.length), 0, dataset);
}
// /** add a dataset to the unpaired list in it's proper order */
// _addToUnpaired: function (dataset) {
//     // currently, unpaired is natural sorted by name, use binary search to find insertion point
//     var binSearchSortedIndex = (low, hi) => {
//         if (low === hi) {
//             return low;
//         }

//         var mid = Math.floor((hi - low) / 2) + low;

//         var compared = naturalSort(dataset.name, this.workingElements[mid].name);

//         if (compared < 0) {
//             return binSearchSortedIndex(low, mid);
//         } else if (compared > 0) {
//             return binSearchSortedIndex(mid + 1, hi);
//         }
//         // walk the equal to find the last
//         while (this.workingElements[mid] && this.workingElements[mid].name === dataset.name) {
//             mid++;
//         }
//         return mid;
//     };

//     this.workingElements.splice(binSearchSortedIndex(0, this.workingElements.length), 0, dataset);
// },

/**
 * Unpair a pair, removing it from paired, and adding the fwd,rev
 * datasets back into unpaired
 */
function _unpair(pair: DatasetPair) {
    if (!pair) {
        throw new Error(`Bad pair: ${JSON.stringify(pair)}`);
    }
    generatedPairs.value.splice(generatedPairs.value.indexOf(pair), 1);
    _addToUnpaired(pair.forward);
    _addToUnpaired(pair.reverse);

    return pair;
}

/** Unpair all paired datasets */
function unpairAll() {
    const pairs = [];
    while (generatedPairs.value.length) {
        if (generatedPairs.value[0]) {
            pairs.push(_unpair(generatedPairs.value[0]));
        }

        // pairs.push(_unpair(this.generatedPairs[0], { silent: true }));
    }
}
// ===========================================================================

/** Returns an autopair function that uses the provided options.match function */
function autoPairFnBuilder(options: {
    match: (params: {
        matchTo: string;
        possible: string;
        index: number;
        bestMatch: { score: number; index: number };
    }) => { score: number; index: number };
    createPair?: (params: {
        listA: HDASummary[];
        indexA: number;
        listB: HDASummary[];
        indexB: number;
    }) => DatasetPair | undefined;
    preprocessMatch?: (params: {
        matchTo: HDASummary;
        possible: HDASummary;
        index: number;
        bestMatch: { score: number; index: number };
    }) => { matchTo: string; possible: string; index: number; bestMatch: { score: number; index: number } };
    scoreThreshold?: number;
}) {
    options = options || {};
    options.createPair =
        options.createPair ||
        function _defaultCreatePair(params) {
            params = params || {};
            const a = params.listA.splice(params.indexA, 1)[0];
            const b = params.listB.splice(params.indexB, 1)[0];
            if (!a || !b) {
                return undefined;
            }
            const aInBIndex = params.listB.indexOf(a);
            const bInAIndex = params.listA.indexOf(b);
            if (aInBIndex !== -1) {
                params.listB.splice(aInBIndex, 1);
            }
            if (bInAIndex !== -1) {
                params.listA.splice(bInAIndex, 1);
            }
            // return _pair(a, b, { silent: true });
            return _pair(a, b);
        };
    // compile these here outside of the loop
    let _regexps: RegExp[] = [];
    function getRegExps() {
        if (!_regexps.length) {
            _regexps = [new RegExp(forwardFilter.value), new RegExp(reverseFilter.value)];
        }
        return _regexps;
    }
    // mangle params as needed
    options.preprocessMatch =
        options.preprocessMatch ||
        function _defaultPreprocessMatch(params) {
            const regexps = getRegExps();
            return Object.assign(params, {
                matchTo: params.matchTo.name?.replace(regexps[0] || "", ""),
                possible: params.possible.name?.replace(regexps[1] || "", ""),
                index: params.index,
                bestMatch: params.bestMatch,
            });
        };

    return function _strategy(params: { listA: HDASummary[]; listB: HDASummary[] }) {
        params = params || {};
        const listA = params.listA;
        const listB = params.listB;
        let indexA = 0;
        let indexB;

        let bestMatch = {
            score: 0.0,
            index: -1,
        };

        const paired = [];
        while (indexA < listA.length) {
            const matchTo = listA[indexA];
            bestMatch.score = 0.0;

            if (!matchTo) {
                continue;
            }
            for (indexB = 0; indexB < listB.length; indexB++) {
                const possible = listB[indexB] as HDASummary;
                if (listA[indexA] !== listB[indexB]) {
                    bestMatch = options.match(
                        options.preprocessMatch!({
                            matchTo: matchTo,
                            possible: possible,
                            index: indexB,
                            bestMatch: bestMatch,
                        })
                    );
                    if (bestMatch.score === 1.0) {
                        break;
                    }
                }
            }
            const scoreThreshold = options.scoreThreshold ? options.scoreThreshold : MATCH_PERCENTAGE;
            if (bestMatch.score >= scoreThreshold) {
                const createdPair = options.createPair!({
                    listA: listA,
                    indexA: indexA,
                    listB: listB,
                    indexB: bestMatch.index,
                });
                if (createdPair) {
                    paired.push(createdPair);
                }
            } else {
                indexA += 1;
            }
            if (!listA.length || !listB.length) {
                return paired;
            }
        }
        return paired;
    };
}

function changeFilters(filter: keyof typeof COMMON_FILTERS) {
    forwardFilter.value = COMMON_FILTERS[filter][0] as string;
    reverseFilter.value = COMMON_FILTERS[filter][1] as string;
}

function addUploadedFiles(files: HDASummary[]) {
    // Any uploaded files are added to workingElements in _elementsSetUp
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

async function clickedCreate(collectionName: string) {
    checkForDuplicates();
    if (state.value == "build") {
        emit("clicked-create", generatedPairs.value, collectionName, hideSourceItems.value);
    }
}

function checkForDuplicates() {
    const existingPairNames: Record<string, boolean> = {};
    duplicatePairNames.value = [];
    let valid = true;
    generatedPairs.value.forEach((pair) => {
        if (Object.prototype.hasOwnProperty.call(existingPairNames, pair.name)) {
            valid = false;
            duplicatePairNames.value.push(pair.name);
        }
        existingPairNames[pair.name] = true;
    });
    state.value = valid ? "build" : "duplicates";
}

// TODO: Where is this being used?
// function stripExtension(name: string) {
//     return name.includes(".") ? name.substring(0, name.lastIndexOf(".")) : name;
// }

/** Return the concat'd longest common prefix and suffix from two strings */
function _naiveStartingAndEndingLCS(s1: string, s2: string) {
    var fwdLCS = "";
    var revLCS = "";
    var i = 0;
    var j = 0;
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
    <div class="paired-list-collection-creator">
        <div v-if="state == 'error'">
            <BAlert show variant="danger">
                {{ ERROR_TEXT }}
            </BAlert>
        </div>
        <div v-else>
            <div v-if="fromSelection && returnInvalidElementsLength">
                <BAlert show variant="warning" dismissible>
                    {{ INVALID_HEADER }}
                    <ul>
                        <li v-for="problem in returnInvalidElements" :key="problem">
                            {{ problem }}
                        </li>
                    </ul>
                </BAlert>
            </div>
            <div v-if="!autoPairsPossible">
                <BAlert show variant="danger" dismissible @dismissed="autoPairsPossible = true">
                    {{
                        localize(
                            "Could not automatically create any pairs from the given dataset names. You may want to choose or enter different filters and try auto-pairing again."
                        )
                    }}
                    <span v-if="fromSelection">
                        <a class="cancel-text" href="javascript:void(0)" role="button" @click="emit('on-cancel')">
                            {{ CANCEL_TEXT }}
                        </a>
                        {{ allInvalidElementsPartTwo }}
                    </span>
                </BAlert>
            </div>
            <div v-if="state == 'duplicates'">
                <BAlert show variant="danger">
                    {{
                        localize("Collections cannot have duplicated names. The following list names are duplicated: ")
                    }}
                    <ul>
                        <li v-for="name in duplicatePairNames" :key="name">{{ name }}</li>
                    </ul>
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
                :no-items="props.initialElements.length == 0 && !props.fromSelection"
                @add-uploaded-files="addUploadedFiles"
                @onUpdateHideSourceItems="hideSourceItems = $event"
                @clicked-create="clickedCreate"
                @remove-extensions-toggle="removeExtensionsToggle">
                <template v-slot:help-content>
                    <!-- TODO: Update help content for case where `fromSelection` is false -->
                    <p>
                        {{
                            localize(
                                [
                                    "Collections of paired datasets are ordered lists of dataset pairs (often forward and reverse reads). ",
                                    "These collections can be passed to tools and workflows in order to have analyses done on each member of ",
                                    "the entire group. This interface allows you to create a collection, choose which datasets are paired, ",
                                    "and re-order the final collection.",
                                ].join("")
                            )
                        }}
                    </p>
                    <p>
                        {{ localize("Unpaired datasets are shown in the") }}
                        <i data-target=".unpaired-columns">
                            {{ localize("unpaired section") }}
                        </i>
                        {{ "." }}
                        {{ localize("Paired datasets are shown in the") }}
                        <i data-target=".paired-columns">
                            {{ localize("paired section") }}
                        </i>
                        {{ "." }}
                    </p>
                    <ul>
                        {{
                            localize("To pair datasets, you can:")
                        }}
                        <li>
                            {{ localize("Click a dataset in the") }}
                            <i data-target=".forward-column">
                                {{ localize("forward column") }}
                            </i>
                            {{ localize("to select it then click a dataset in the") }}
                            <i data-target=".reverse-column">
                                {{ localize("reverse column") }}
                            </i>
                        </li>
                        <li>
                            {{
                                localize(
                                    "Click one of the Pair these datasets buttons in the middle column to pair the datasets in a particular row."
                                )
                            }}
                        </li>
                        <li>
                            {{ localize("Click") }}
                            <i data-target=".autopair-link">
                                {{ localize("Auto-pair") }}
                            </i>
                            {{ localize("to have your datasets automatically paired based on name.") }}
                        </li>
                    </ul>
                    <ul>
                        {{
                            localize("You can filter what is shown in the unpaired sections by:")
                        }}
                        <li>
                            {{ localize("Entering partial dataset names in either the ") }}
                            <i data-target=".forward-unpaired-filter input">
                                {{ localize("forward filter") }}
                            </i>
                            {{ localize("or ") }}
                            <i data-target=".reverse-unpaired-filter input">
                                {{ localize("reverse filter") }}
                            </i>
                            {{ "." }}
                        </li>
                        <li>
                            {{
                                localize(
                                    "Choosing from a list of preset filters by clicking the arrow beside the filter input."
                                )
                            }}
                        </li>
                        <li>
                            {{ localize("Entering regular expressions to match dataset names. See:") }}
                            <a
                                href="https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Regular_Expressions"
                                target="_blank">
                                {{ localize("MDN's JavaScript Regular Expression Tutorial") }}</a
                            >
                            {{ localize("Note: forward slashes (\\) are not needed.") }}
                        </li>
                        <li>
                            {{ localize("Clearing the filters by clicking the ") }}
                            <i data-target=".clear-filters-link">
                                {{ localize("Clear filters link") }}
                            </i>
                            {{ "." }}
                        </li>
                    </ul>
                    <p>
                        {{ localize("To unpair individual dataset pairs, click the ") }}
                        <i data-target=".unpair-btn">
                            {{ localize("unpair buttons (") }}
                            <span class="fa fa-unlink"></span>
                            {{ ")" }}
                        </i>
                        {{ localize("Click the") }}
                        <i data-target=".unpair-all-link">
                            {{ localize("Unpair all") }}
                        </i>
                        {{ localize("link to unpair all pairs.") }}
                    </p>
                    <p>
                        {{
                            localize(
                                'You can include or remove the file extensions (e.g. ".fastq") from your pair names by toggling the'
                            )
                        }}
                        <i data-target=".remove-extensions-prompt">
                            {{ localize("Remove file extensions from pair names?") }}
                        </i>
                        {{ localize("control.") }}
                    </p>
                    <p>
                        {{ localize("Once your collection is complete, enter a") }}
                        <i data-target=".collection-name">
                            {{ localize("name") }}
                        </i>
                        {{ localize("and click ") }}
                        <i data-target=".create-collection">
                            {{ localize("Create list") }}
                        </i>
                        {{ localize(". (Note: you do not have to pair all unpaired datasets to finish.)") }}
                    </p>
                </template>
                <template v-slot:middle-content>
                    <div v-if="noElementsSelected">
                        <BAlert show variant="warning" dismissible>
                            {{ noElementsHeader }}
                            {{ ALL_INVALID_ELEMENTS_PART_ONE }}
                            <a class="cancel-text" href="javascript:void(0)" role="button" @click="emit('on-cancel')">
                                {{ CANCEL_TEXT }}
                            </a>
                            {{ allInvalidElementsPartTwo }}
                        </BAlert>
                    </div>
                    <div v-else-if="allElementsAreInvalid">
                        <BAlert v-if="!fromSelection" show variant="warning">
                            {{
                                localize(
                                    "No elements in your history are valid for this collection. You may need to switch to a different history."
                                )
                            }}
                            <span v-if="extensions?.length">
                                {{ localize("The following extensions are required for this collection: ") }}
                                <ul>
                                    <li v-for="extension in extensions" :key="extension">
                                        {{ extension }}
                                    </li>
                                </ul>
                            </span>
                        </BAlert>
                        <BAlert v-else show variant="warning" dismissible>
                            {{ INVALID_HEADER }}
                            <ul>
                                <li v-for="problem in returnInvalidElements" :key="problem">
                                    {{ problem }}
                                </li>
                            </ul>
                            {{ ALL_INVALID_ELEMENTS_PART_ONE }}
                            <a class="cancel-text" href="javascript:void(0)" role="button" @click="emit('on-cancel')">
                                {{ CANCEL_TEXT }}
                            </a>
                            {{ allInvalidElementsPartTwo }}
                        </BAlert>
                    </div>
                    <div v-else-if="tooFewElementsSelected">
                        <div v-if="returnInvalidElementsLength">
                            <BAlert show variant="warning" dismissible>
                                {{ INVALID_HEADER }}
                                <ul>
                                    <li v-for="problem in returnInvalidElements" :key="problem">
                                        {{ problem }}
                                    </li>
                                </ul>
                            </BAlert>
                        </div>
                        <BAlert show variant="warning" dismissible>
                            {{ ALL_INVALID_ELEMENTS_PART_ONE }}
                            <a class="cancel-text" href="javascript:void(0)" role="button" @click="emit('on-cancel')">
                                {{ CANCEL_TEXT }}
                            </a>
                            {{ allInvalidElementsPartTwo }}
                        </BAlert>
                    </div>
                    <div v-else>
                        <BCard no-body class="mb-2">
                            <BCardHeader
                                class="d-flex justify-content-between align-items-center unselectable"
                                role="button"
                                @click="showPairingSection = !showPairingSection">
                                <Heading size="sm">Pairing</Heading>
                                <i class="text-muted">
                                    {{ localize("Click to hide/show datasets to pair") }}
                                    <FontAwesomeIcon
                                        :icon="showPairingSection ? faAngleUp : faAngleDown"
                                        size="lg"
                                        fixed-width />
                                </i>
                            </BCardHeader>
                            <BCardBody v-show="showPairingSection" class="pairing-split-parent">
                                <div class="column-headers vertically-spaced flex-column-container">
                                    <div class="forward-column flex-column column">
                                        <div class="column-header">
                                            <div class="column-title">
                                                <span class="title">
                                                    {{ numOfUnpairedForwardElements }}
                                                    {{ localize("unpaired forward") }}
                                                </span>
                                                <span class="title-info unpaired-info">
                                                    {{ numOfFilteredOutForwardElements }} {{ localize("filtered out") }}
                                                </span>
                                            </div>
                                            <div
                                                class="unpaired-filter forward-unpaired-filter search-input search-query input-group">
                                                <label for="forward-filter" class="sr-only">{{
                                                    FILTER_TEXT_TITLE
                                                }}</label>
                                                <input
                                                    id="foward-filter"
                                                    v-model="forwardFilter"
                                                    type="text"
                                                    :placeholder="FILTER_TEXT_PLACEHOLDER"
                                                    :title="FILTER_TEXT_TITLE" />
                                                <div class="input-group-append" :title="CHOOSE_FILTER_TITLE">
                                                    <button
                                                        class="btn btn-outline-secondary dropdown-toggle"
                                                        type="button"
                                                        data-toggle="dropdown"
                                                        aria-haspopup="true"
                                                        aria-expanded="false"></button>
                                                    <div class="dropdown-menu">
                                                        <a
                                                            class="dropdown-item"
                                                            href="javascript:void(0);"
                                                            @click="changeFilters('illumina')">
                                                            _1
                                                        </a>
                                                        <a
                                                            class="dropdown-item"
                                                            href="javascript:void(0);"
                                                            @click="changeFilters('Rs')">
                                                            _R1
                                                        </a>
                                                        <a
                                                            class="dropdown-item"
                                                            href="javascript:void(0);"
                                                            @click="changeFilters('dot12s')">
                                                            .1.fastq
                                                        </a>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="paired-column flex-column no-flex column">
                                        <BButtonGroup vertical>
                                            <BButton
                                                class="clear-filters-link"
                                                size="sm"
                                                :variant="hasFilter ? 'danger' : 'secondary'"
                                                @click="clickClearFilters">
                                                <FontAwesomeIcon :icon="faTimes" fixed-width />
                                                {{ localize("Clear Filters") }}
                                            </BButton>
                                            <BButton
                                                class="autopair-link"
                                                size="sm"
                                                :title="autoPairButton.text"
                                                :variant="autoPairButton.variant"
                                                @click="clickAutopair">
                                                <FontAwesomeIcon :icon="autoPairButton.icon" fixed-width />
                                                {{ localize("Auto-pair") }}
                                            </BButton>
                                        </BButtonGroup>
                                    </div>
                                    <div class="reverse-column flex-column column">
                                        <div class="column-header">
                                            <div class="column-title">
                                                <span class="title">
                                                    {{ numOfUnpairedReverseElements }}
                                                    {{ localize("unpaired reverse") }}
                                                </span>
                                                <span class="title-info unpaired-info">
                                                    {{ numOfFilteredOutReverseElements }}
                                                    {{ localize("filtered out") }}</span
                                                >
                                            </div>
                                            <div
                                                class="unpaired-filter reverse-unpaired-filter justify-content-end search-input search-query input-group">
                                                <label for="reverse-filter" class="sr-only">{{
                                                    FILTER_TEXT_TITLE
                                                }}</label>
                                                <input
                                                    id="reverse-filter"
                                                    v-model="reverseFilter"
                                                    type="text"
                                                    :placeholder="FILTER_TEXT_PLACEHOLDER"
                                                    :title="FILTER_TEXT_TITLE" />
                                                <div class="input-group-append" :title="CHOOSE_FILTER_TITLE">
                                                    <button
                                                        class="btn btn-outline-secondary dropdown-toggle"
                                                        type="button"
                                                        data-toggle="dropdown"
                                                        aria-haspopup="true"
                                                        aria-expanded="false"></button>
                                                    <div class="dropdown-menu">
                                                        <a
                                                            class="dropdown-item"
                                                            href="javascript:void(0);"
                                                            @click="changeFilters('illumina')">
                                                            _2
                                                        </a>
                                                        <a
                                                            class="dropdown-item"
                                                            href="javascript:void(0);"
                                                            @click="changeFilters('Rs')">
                                                            _R2
                                                        </a>
                                                        <a
                                                            class="dropdown-item"
                                                            href="javascript:void(0);"
                                                            @click="changeFilters('dot12s')">
                                                            .2.fastq
                                                        </a>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div class="pairing-split-child">
                                    <div v-if="noUnpairedElementsDisplayed">
                                        <BAlert show variant="warning">
                                            {{ localize("No datasets were found matching the current filters.") }}
                                        </BAlert>
                                    </div>
                                    <div class="unpaired-columns flex-column-container scroll-container flex-row">
                                        <div class="forward-column flex-column column truncate">
                                            <ol class="column-datasets">
                                                <UnpairedDatasetElementView
                                                    v-for="element in forwardElements"
                                                    :key="element.id"
                                                    :class="{
                                                        selected:
                                                            selectedForwardElement &&
                                                            element.id === selectedForwardElement.id,
                                                    }"
                                                    :disabled="element.id === selectedReverseElement?.id"
                                                    :element="element"
                                                    @element-is-selected="forwardElementSelected" />
                                            </ol>
                                        </div>
                                        <div class="paired-column flex-column no-flex column truncate">
                                            <ol
                                                v-if="forwardFilter !== '' && reverseFilter !== ''"
                                                class="column-datasets">
                                                <li
                                                    v-for="(pairableElement, index) in pairableElements"
                                                    :key="index"
                                                    class="dataset"
                                                    role="button"
                                                    tabindex="0"
                                                    @keyup.enter="
                                                        _pair(pairableElement.forward, pairableElement.reverse)
                                                    "
                                                    @click="_pair(pairableElement.forward, pairableElement.reverse)">
                                                    {{ localize("Pair these datasets") }}
                                                </li>
                                            </ol>
                                        </div>
                                        <div class="reverse-column flex-column column truncate">
                                            <ol class="column-datasets">
                                                <UnpairedDatasetElementView
                                                    v-for="element in reverseElements"
                                                    :key="element.id"
                                                    :class="{
                                                        selected:
                                                            selectedReverseElement &&
                                                            element.id == selectedReverseElement.id,
                                                    }"
                                                    :disabled="element.id === selectedForwardElement?.id"
                                                    :element="element"
                                                    @element-is-selected="reverseElementSelected" />
                                            </ol>
                                        </div>
                                    </div>
                                </div>
                            </BCardBody>
                        </BCard>
                        <div>
                            <div class="pairing-split-child">
                                <div class="column-header">
                                    <div class="column-title paired-column-title" data-description="number of pairs">
                                        <span class="title"> {{ numOfPairs }} {{ localize("pairs") }}</span>
                                    </div>
                                    <BButton
                                        v-if="generatedPairs.length > 0"
                                        variant="link"
                                        size="sm"
                                        @click.stop="unpairAll">
                                        <FontAwesomeIcon :icon="faUnlink" fixed-width />
                                        {{ localize("Unpair all") }}
                                    </BButton>
                                </div>
                                <div class="paired-columns flex-column-container scroll-container flex-row">
                                    <ol class="column-datasets">
                                        <draggable
                                            v-model="generatedPairs"
                                            handle=".dataset"
                                            chosen-class="dragged-pair">
                                            <PairedElementView
                                                v-for="pair in generatedPairs"
                                                :key="`${pair.forward.id}-${pair.reverse.id}`"
                                                :pair="pair"
                                                @onPairRename="(name) => (pair.name = name)"
                                                @onUnpair="clickUnpair(pair)" />
                                        </draggable>
                                    </ol>
                                </div>
                            </div>
                        </div>
                    </div>
                </template>
            </CollectionCreator>
        </div>
    </div>
</template>

<style lang="scss">
$fa-font-path: "../../../node_modules/@fortawesome/fontawesome-free/webfonts/";
@import "~@fortawesome/fontawesome-free/scss/_variables";
@import "~@fortawesome/fontawesome-free/scss/solid";
@import "~@fortawesome/fontawesome-free/scss/fontawesome";
@import "~@fortawesome/fontawesome-free/scss/brands";
.paired-column {
    text-align: center;
    // mess with these two to make center more/scss priority
    width: 22%;
}
.column-headers {
    margin-bottom: 8px;
}
.input-group {
    width: auto;
    border: none;
}
ol.column-datasets {
    width: auto;
}
li.dataset.paired {
    text-align: center;
}
.column-datasets {
    list-style: none;
    overflow: hidden;
    .dragged-pair {
        border-top: 2px solid black;
    }
    .unpair-btn {
        border: none;
        flex-shrink: 0;
    }
    .dataset {
        height: 32px;
        margin-top: 2px;
        &:last-of-type {
            margin-bottom: 2px;
        }
        border: 1px solid lightgrey;
        border-radius: 3px;
        padding: 0 8px 0 8px;
        line-height: 28px;
        cursor: pointer;
        &.unpaired {
            border-color: grey;
        }
        &.paired {
            white-space: nowrap;
            overflow: hidden;
            border: 2px solid grey;
            background: #aff1af;
            text-align: center;
            span {
                display: inline-block;
            }
            .forward-dataset-name {
                text-align: right;
                border-right: 1px solid grey;
                padding-right: 8px;
            }
            .pair-name-column {
                padding: 0 8px;
                text-align: center;
            }
            .reverse-dataset-name {
                border-left: 1px solid grey;
                padding-left: 8px;
            }
        }
        &:hover {
            border-color: black;
        }
        &.selected {
            border-color: black;
            background: black;
            color: white;
            a {
                color: white;
            }
        }
    }
}
// ---- unpaired
.unpaired-columns {
    // @extend .flex-bordered-vertically;
    .forward-column {
        .dataset.unpaired {
            margin-right: 32px;
        }
    }
    .paired-column {
        .dataset.unpaired {
            border-color: lightgrey;
            color: lightgrey;
            &:hover {
                border-color: black;
                color: black;
            }
        }
    }
    .reverse-column {
        .dataset.unpaired {
            margin-left: 32px;
        }
    }
    .dataset.unpaired {
        white-space: nowrap;
        overflow: hidden;
        box-sizing: border-box;
        position: relative;
        .element-name {
            display: inline-block;
            position: relative;
            min-width: 100%;
        }
        &:hover {
            .element-name.moves {
                animation: move-right 1s linear forwards;
            }
        }
    }
    @keyframes move-right {
        10% {
            transform: translate(0, 0);
            left: 0%;
        }
        100% {
            transform: translate(-100%, 0);
            left: 100%;
        }
    }
}

.column-header {
    width: 100%;
    text-align: center;
    justify-content: end;
    .column-title {
        display: inline;
    }
    & > *:not(:last-child) {
        margin-right: 8px;
    }
    .remove-extensions-link {
        display: none;
    }
}
// ---- paired datasets
.paired-columns {
    // @extend .flex-bordered-vertically;
    margin-bottom: 8px;
    .column-datasets {
        width: 100%;
    }
    .empty-message {
        text-align: center;
    }
}
.pairing-split-parent {
    display: flex;
    flex-direction: column;
    min-height: 400px;
}

.pairing-split-child {
    flex: 1;
    overflow-y: auto;
}
</style>
