<template>
    <div class="paired-list-collection-creator">
        <div v-if="state == 'error'">
            <b-alert show variant="danger">
                {{ errorText }}
            </b-alert>
        </div>
        <div v-else>
            <div v-if="noElementsSelected">
                <b-alert show variant="warning" dismissible>
                    {{ noElementsHeader }}
                    {{ allInvalidElementsPartOne }}
                    <a class="cancel-text" href="javascript:void(0)" role="button" @click="oncancel">
                        {{ cancelText }}
                    </a>
                    {{ allInvalidElementsPartTwo }}
                </b-alert>
                <div class="float-left">
                    <button class="cancel-create btn" tabindex="-1" @click="oncancel">
                        {{ l("Cancel") }}
                    </button>
                </div>
            </div>
            <div v-else-if="allElementsAreInvalid">
                <b-alert show variant="warning" dismissible>
                    {{ invalidHeader }}
                    <ul>
                        <li v-for="problem in returnInvalidElements" :key="problem">
                            {{ problem }}
                        </li>
                    </ul>
                    {{ allInvalidElementsPartOne }}
                    <a class="cancel-text" href="javascript:void(0)" role="button" @click="oncancel">
                        {{ cancelText }}
                    </a>
                    {{ allInvalidElementsPartTwo }}
                </b-alert>
                <div class="float-left">
                    <button class="cancel-create btn" tabindex="-1" @click="oncancel">
                        {{ l("Cancel") }}
                    </button>
                </div>
            </div>
            <div v-else-if="tooFewElementsSelected">
                <div v-if="returnInvalidElementsLength">
                    <b-alert show variant="warning" dismissible>
                        {{ invalidHeader }}
                        <ul>
                            <li v-for="problem in returnInvalidElements" :key="problem">
                                {{ problem }}
                            </li>
                        </ul>
                    </b-alert>
                </div>
                <b-alert show variant="warning" dismissible>
                    {{ allInvalidElementsPartOne }}
                    <a class="cancel-text" href="javascript:void(0)" role="button" @click="oncancel">
                        {{ cancelText }}
                    </a>
                    {{ allInvalidElementsPartTwo }}
                </b-alert>
                <div class="float-left">
                    <button class="cancel-create btn" tabindex="-1" @click="oncancel">
                        {{ l("Cancel") }}
                    </button>
                </div>
            </div>
            <div v-else>
                <div v-if="returnInvalidElementsLength">
                    <b-alert show variant="warning" dismissible>
                        {{ invalidHeader }}
                        <ul>
                            <li v-for="problem in returnInvalidElements" :key="problem">
                                {{ problem }}
                            </li>
                        </ul>
                    </b-alert>
                </div>
                <div v-if="!initialPairsPossible">
                    <b-alert show variant="danger" dismissible>
                        {{
                            l(
                                "Could not automatically create any pairs from the given dataset names. You may want to choose or enter different filters and try auto-pairing again."
                            )
                        }}
                        <a class="cancel-text" href="javascript:void(0)" role="button" @click="oncancel">
                            {{ cancelText }}
                        </a>
                        {{ allInvalidElementsPartTwo }}
                    </b-alert>
                </div>
                <div v-if="state == 'duplicates'">
                    <b-alert show variant="danger">
                        {{ l("Collections cannot have duplicated names. The following list names are duplicated: ") }}
                        <ul>
                            <li v-for="name in duplicatePairNames" :key="name">{{ name }}</li>
                        </ul>
                        {{ l("Please fix these duplicates and try again.") }}
                    </b-alert>
                </div>
                <collection-creator
                    :oncancel="oncancel"
                    :hide-source-items="hideSourceItems"
                    :render-extensions-toggle="true"
                    :extensions-toggle="removeExtensions"
                    @onUpdateHideSourceItems="onUpdateHideSourceItems"
                    @clicked-create="clickedCreate"
                    @remove-extensions-toggle="removeExtensionsToggle">
                    <template v-slot:help-content>
                        <p>
                            {{
                                l(
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
                            {{ l("Unpaired datasets are shown in the") }}
                            <i data-target=".unpaired-columns">
                                {{ l("unpaired section") }}
                            </i>
                            {{ "." }}
                            {{ l("Paired datasets are shown in the") }}
                            <i data-target=".paired-columns">
                                {{ l("paired section") }}
                            </i>
                            {{ "." }}
                        </p>
                        <ul>
                            {{
                                l("To pair datasets, you can:")
                            }}
                            <li>
                                {{ l("Click a dataset in the") }}
                                <i data-target=".forward-column">
                                    {{ l("forward column") }}
                                </i>
                                {{ l("to select it then click a dataset in the") }}
                                <i data-target=".reverse-column">
                                    {{ l("reverse column") }}
                                </i>
                            </li>
                            <li>
                                {{
                                    l(
                                        "Click one of the Pair these datasets buttons in the middle column to pair the datasets in a particular row."
                                    )
                                }}
                            </li>
                            <li>
                                {{ l("Click") }}
                                <i data-target=".autopair-link">
                                    {{ l("Auto-pair") }}
                                </i>
                                {{ l("to have your datasets automatically paired based on name.") }}
                            </li>
                        </ul>
                        <ul>
                            {{
                                l("You can filter what is shown in the unpaired sections by:")
                            }}
                            <li>
                                {{ l("Entering partial dataset names in either the ") }}
                                <i data-target=".forward-unpaired-filter input">
                                    {{ l("forward filter") }}
                                </i>
                                {{ l("or ") }}
                                <i data-target=".reverse-unpaired-filter input">
                                    {{ l("reverse filter") }}
                                </i>
                                {{ "." }}
                            </li>
                            <li>
                                {{
                                    l(
                                        "Choosing from a list of preset filters by clicking the arrow beside the filter input."
                                    )
                                }}
                            </li>
                            <li>
                                {{ l("Entering regular expressions to match dataset names. See:") }}
                                <a
                                    href="https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Regular_Expressions"
                                    target="_blank">
                                    {{ l("MDN's JavaScript Regular Expression Tutorial") }}</a
                                >
                                {{ l("Note: forward slashes (\\) are not needed.") }}
                            </li>
                            <li>
                                {{ l("Clearing the filters by clicking the ") }}
                                <i data-target=".clear-filters-link">
                                    {{ l("Clear filters link") }}
                                </i>
                                {{ "." }}
                            </li>
                        </ul>
                        <p>
                            {{ l("To unpair individual dataset pairs, click the ") }}
                            <i data-target=".unpair-btn">
                                {{ l("unpair buttons (") }}
                                <span class="fa fa-unlink"></span>
                                {{ ")" }}
                            </i>
                            {{ l("Click the") }}
                            <i data-target=".unpair-all-link">
                                {{ l("Unpair all") }}
                            </i>
                            {{ l("link to unpair all pairs.") }}
                        </p>
                        <p>
                            {{
                                l(
                                    'You can include or remove the file extensions (e.g. ".fastq") from your pair names by toggling the'
                                )
                            }}
                            <i data-target=".remove-extensions-prompt">
                                {{ l("Remove file extensions from pair names?") }}
                            </i>
                            {{ l("control.") }}
                        </p>
                        <p>
                            {{ l("Once your collection is complete, enter a") }}
                            <i data-target=".collection-name">
                                {{ l("name") }}
                            </i>
                            {{ l("and click ") }}
                            <i data-target=".create-collection">
                                {{ l("Create list") }}
                            </i>
                            {{ l(". (Note: you do not have to pair all unpaired datasets to finish.)") }}
                        </p>
                    </template>
                    <template v-slot:middle-content>
                        <div class="column-headers vertically-spaced flex-column-container">
                            <div class="forward-column flex-column column">
                                <div class="column-header">
                                    <div class="column-title">
                                        <span class="title">
                                            {{ numOfUnpairedForwardElements }}
                                            {{ l("unpaired forward") }}
                                        </span>
                                        <span class="title-info unpaired-info">
                                            {{ numOfFilteredOutForwardElements }} {{ l("filtered out") }}
                                        </span>
                                    </div>
                                    <div
                                        class="unpaired-filter forward-unpaired-filter float-left search-input search-query input-group">
                                        <input
                                            v-model="forwardFilter"
                                            type="text"
                                            :placeholder="filterTextPlaceholder"
                                            title="filterTextTitle" />
                                        <div class="input-group-append" :title="chooseFilterTitle">
                                            <button
                                                class="btn btn-outline-secondary dropdown-toggle"
                                                type="button"
                                                data-toggle="dropdown"
                                                aria-haspopup="true"
                                                aria-expanded="false"></button>
                                            <div class="dropdown-menu">
                                                <a class="dropdown-item" @click="changeFilters('illumina')">_1</a>
                                                <a class="dropdown-item" @click="changeFilters('Rs')">_R1</a>
                                                <a class="dropdown-item" @click="changeFilters('dot12s')">.1.fastq</a>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="paired-column flex-column no-flex column">
                                <div class="column-header">
                                    <a
                                        class="clear-filters-link"
                                        href="javascript:void(0);"
                                        role="button"
                                        @click="clickClearFilters">
                                        {{ l("Clear Filters") }}
                                    </a>
                                    <br />
                                    <a
                                        class="autopair-link"
                                        href="javascript:void(0);"
                                        role="button"
                                        @click="clickAutopair">
                                        {{ l("Auto-pair") }}
                                    </a>
                                </div>
                            </div>
                            <div class="reverse-column flex-column column">
                                <div class="column-header">
                                    <div class="column-title">
                                        <span class="title">
                                            {{ numOfUnpairedReverseElements }}
                                            {{ l("unpaired reverse") }}
                                        </span>
                                        <span class="title-info unpaired-info">
                                            {{ numOfFilteredOutReverseElements }} {{ l("filtered out") }}</span
                                        >
                                    </div>
                                    <div
                                        class="unpaired-filter reverse-unpaired-filter float-left search-input search-query input-group">
                                        <input
                                            v-model="reverseFilter"
                                            type="text"
                                            :placeholder="filterTextPlaceholder"
                                            title="filterTextTitle" />
                                        <div class="input-group-append" :title="chooseFilterTitle">
                                            <button
                                                class="btn btn-outline-secondary dropdown-toggle"
                                                type="button"
                                                data-toggle="dropdown"
                                                aria-haspopup="true"
                                                aria-expanded="false"></button>
                                            <div class="dropdown-menu">
                                                <a class="dropdown-item" @click="changeFilters('illumina')">_2</a>
                                                <a class="dropdown-item" @click="changeFilters('Rs')">_R2</a>
                                                <a class="dropdown-item" @click="changeFilters('dot12s')">.2.fastq</a>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="pairing-split-parent">
                            <div class="pairing-split-child">
                                <div v-if="noUnpairedElementsDisplayed">
                                    <b-alert show variant="warning">
                                        {{ l("No datasets were found matching the current filters.") }}
                                    </b-alert>
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
                                                        element.id == selectedForwardElement.id,
                                                }"
                                                :element="element"
                                                @element-is-selected="forwardElementSelected" />
                                        </ol>
                                    </div>
                                    <div class="paired-column flex-column no-flex column truncate">
                                        <ol v-if="forwardFilter !== '' && reverseFilter !== ''" class="column-datasets">
                                            <li
                                                v-for="(pairableElement, index) in pairableElements"
                                                :key="index"
                                                class="dataset"
                                                @click="_pair(pairableElement.forward, pairableElement.reverse)">
                                                {{ l("Pair these datasets") }}
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
                                                :element="element"
                                                @element-is-selected="reverseElementSelected" />
                                        </ol>
                                    </div>
                                </div>
                            </div>
                            <div class="pairing-split-child">
                                <div class="column-header">
                                    <div class="column-title paired-column-title">
                                        <span class="title"> {{ numOfPairs }} {{ l(" pairs") }}</span>
                                    </div>
                                    <a
                                        class="unpair-all-link"
                                        href="javascript:void(0);"
                                        role="button"
                                        @click="unpairAll">
                                        {{ l("Unpair all") }}
                                    </a>
                                </div>
                                <div class="paired-columns flex-column-container scroll-container flex-row">
                                    <ol class="column-datasets">
                                        <draggable v-model="pairedElements" @start="drag = true" @end="drag = false">
                                            <PairedElementView
                                                v-for="pair in pairedElements"
                                                :key="pair.id"
                                                :pair="pair"
                                                :unlink-fn="clickUnpair(pair)"
                                                @onPairRename="(name) => (pair.name = name)" />
                                        </draggable>
                                    </ol>
                                </div>
                            </div>
                        </div>
                    </template>
                </collection-creator>
            </div>
        </div>
    </div>
</template>
<script>
import BootstrapVue from "bootstrap-vue";
import STATES from "mvc/dataset/states";
import levenshteinDistance from "utils/levenshtein";
import _l from "utils/localization";
import naturalSort from "utils/natural-sort";
import Vue from "vue";
import draggable from "vuedraggable";

import mixin from "./common/mixin";
import PairedElementView from "./PairedElementView";
import UnpairedDatasetElementView from "./UnpairedDatasetElementView";

Vue.use(BootstrapVue);
export default {
    components: {
        UnpairedDatasetElementView,
        PairedElementView,
        draggable,
    },
    mixins: [mixin],
    data: function () {
        return {
            state: "build", //error, duplicates
            dragToChangeTitle: _l("Drag to change"),
            chooseFilterTitle: _l("Choose from common filters"),
            filterTextPlaceholder: _l("Filter text"),
            filterTextTitle: _l("Use this box to filter elements, using simple matching or regular expressions."),
            pairedElements: [],
            unpairedElements: [],
            commonFilters: {
                illumina: ["_1", "_2"],
                Rs: ["_R1", "_R2"],
                dot12s: [".1.fastq", ".2.fastq"],
            },
            DEFAULT_FILTERS: "illumina",
            forwardFilter: "",
            reverseFilter: "",
            automaticallyPair: true,
            initialPairsPossible: true,
            matchPercentage: 0.99,
            twoPassAutoPairing: true,
            removeExtensions: true,
            workingElements: [],

            selectedForwardElement: null,
            selectedReverseElement: null,
            /** autopair by exact match */

            autopairSimple: this.autoPairFnBuilder({
                scoreThreshold: function () {
                    return 0.6;
                },
                match: function _match(params) {
                    params = params || {};
                    if (params.matchTo === params.possible) {
                        return {
                            index: params.index,
                            score: 1.0,
                        };
                    }
                    return params.bestMatch;
                },
            }),
            /** autopair by levenshtein edit distance scoring */
            autopairLevenshtein: this.autoPairFnBuilder({
                scoreThreshold: function () {
                    return this.matchPercentage;
                },
                match: function _matches(params) {
                    params = params || {};

                    var distance = levenshteinDistance(params.matchTo, params.possible);

                    var score = 1.0 - distance / Math.max(params.matchTo.length, params.possible.length);

                    if (score > params.bestMatch.score) {
                        return {
                            index: params.index,
                            score: score,
                        };
                    }
                    return params.bestMatch;
                },
            }),
            /** autopair by longest common substrings scoring */
            autopairLCS: this.autoPairFnBuilder({
                scoreThreshold: function () {
                    return this.matchPercentage;
                },
                match: function _matches(params) {
                    params = params || {};

                    var match = this._naiveStartingAndEndingLCS(params.matchTo, params.possible).length;

                    var score = match / Math.max(params.matchTo.length, params.possible.length);

                    if (score > params.bestMatch.score) {
                        return {
                            index: params.index,
                            score: score,
                        };
                    }
                    return params.bestMatch;
                },
            }),
            strategy: null,
            errorText: _l("Galaxy could not be reached and may be updating.  Try again in a few minutes."),
            invalidHeader: _l("The following selections could not be included due to problems:"),
            allInvalidElementsPartOne: _l("At least two elements are needed for the collection. You may need to"),
            noElementsHeader: _l("No datasets were selected"),
            cancelText: _l("cancel"),
            allInvalidElementsPartTwo: _l("and reselect new elements."),
            duplicatePairNames: [],
        };
    },
    computed: {
        forwardElements: {
            get() {
                return this.filterElements(this.workingElements, this.forwardFilter);
            },
        },
        reverseElements: {
            get() {
                return this.filterElements(this.workingElements, this.reverseFilter);
            },
        },
        pairableElements: {
            get() {
                var pairable = [];
                this.forwardElements.forEach((elem, index) => {
                    if (this.reverseElements[index] && elem.id != this.reverseElements[index].id) {
                        pairable.push({
                            forward: this.forwardElements[index],
                            reverse: this.reverseElements[index],
                        });
                    }
                });
                return pairable;
            },
        },
        numOfUnpairedForwardElements: function () {
            return this.forwardElements.length;
        },
        numOfFilteredOutForwardElements: function () {
            return this.workingElements.length - this.numOfUnpairedForwardElements;
        },
        numOfUnpairedReverseElements: function () {
            return this.reverseElements.length;
        },
        numOfFilteredOutReverseElements: function () {
            return this.workingElements.length - this.numOfUnpairedReverseElements;
        },
        numOfPairs: function () {
            return this.pairedElements.length;
        },
        returnInvalidElementsLength: function () {
            return this.invalidElements.length > 0;
        },
        returnInvalidElements: function () {
            return this.invalidElements;
        },
        allElementsAreInvalid: function () {
            return this.initialElements.length == this.invalidElements.length;
        },
        noElementsSelected: function () {
            return this.initialElements.length == 0;
        },
        tooFewElementsSelected: function () {
            return this.workingElements.length < 2 && this.pairedElements.length == 0;
        },
        showDuplicateError() {
            return this.duplicatePairNames.length > 0;
        },
        noUnpairedElementsDisplayed() {
            return this.numOfUnpairedForwardElements + this.numOfUnpairedReverseElements == 0;
        },
        renderPairButton() {
            return this;
        },
    },
    created() {
        this.strategy = this.autopairLCS;
        //TODO convert to Fwd/Rev
        // Setup inital filters and shallow copy the items
        this.forwardFilter = this.commonFilters[this.DEFAULT_FILTERS][0];
        this.reverseFilter = this.commonFilters[this.DEFAULT_FILTERS][1];
        this._elementsSetUp();
    },
    methods: {
        l(str) {
            // _l conflicts private methods of Vue internals, expose as l instead
            return _l(str);
        },
        removeExtensionsToggle: function () {
            this.removeExtensions = !this.removeExtensions;
            this.pairedElements.forEach((pair, index) => {
                pair.name = this._guessNameForPair(pair.forward, pair.reverse, this.removeExtensions);
            });
        },
        /** set up main data */
        _elementsSetUp: function () {
            /** a list of invalid elements and the reasons they aren't valid */
            this.invalidElements = [];
            //TODO: handle fundamental problem of syncing DOM, views, and list here
            /** data for list in progress */
            this.workingElements = [];
            //TODO: this should maybe be in it's own method as it will get called everytime selected array has two elements and dumps again.
            this.selectedDatasetElems = [];
            this.initialFiltersSet();
            // copy initial list, sort, add ids if needed
            this.workingElements = JSON.parse(JSON.stringify(this.initialElements.slice(0)));
            this._ensureElementIds();
            this._validateElements();
            this._sortInitialList();
            //attempt to autopair
            if (this.automaticallyPair == true) {
                this.autoPair();
                this.initialPairsPossible = this.pairedElements.length > 0;
            }
        },
        initialFiltersSet: function () {
            let illumina = 0;
            let dot12s = 0;
            let Rs = 0;
            //should we limit the forEach? What if there are 1000s of elements?
            this.initialElements.forEach((element) => {
                if (element.name.includes(".1.fastq") || element.name.includes(".2.fastq")) {
                    dot12s++;
                } else if (element.name.includes("_R1") || element.name.includes("_R2")) {
                    Rs++;
                } else if (element.name.includes("_1") || element.name.includes("_2")) {
                    illumina++;
                }
            });

            if (illumina > dot12s && illumina > Rs) {
                this.changeFilters("illumina");
            } else if (dot12s > illumina && dot12s > Rs) {
                this.changeFilters("dot12s");
            } else if (Rs > illumina && Rs > dot12s) {
                this.changeFilters("Rs");
            } else {
                this.changeFilters("illumina");
            }
        },
        /** add ids to dataset objs in initial list if none */
        _ensureElementIds: function () {
            this.workingElements.forEach((element) => {
                if (!Object.prototype.hasOwnProperty.call(element, "id")) {
                    element.id = element._uid;
                }
            });
            return this.workingElements;
        },
        // /** separate working list into valid and invalid elements for this collection */
        _validateElements: function () {
            this.workingElements = this.workingElements.filter((element) => {
                var problem = this._isElementInvalid(element);
                if (problem) {
                    this.invalidElements.push(element.name + "  " + problem);
                }
                return !problem;
            });
            return this.workingElements;
        },
        /** describe what is wrong with a particular element if anything */
        _isElementInvalid: function (element) {
            if (element.history_content_type === "dataset_collection") {
                return _l("is a collection, this is not allowed");
            }
            var validState = element.state === STATES.OK || STATES.NOT_READY_STATES.includes(element.state);
            if (!validState) {
                return _l("has errored, is paused, or is not accessible");
            }
            if (element.deleted || element.purged) {
                return _l("has been deleted or purged");
            }
            return null;
        },
        /** sort initial list */
        _sortInitialList: function () {
            //console.debug( '-- _sortInitialList' );
            this._sortDatasetList(this.workingElements);
        },

        /** sort a list of datasets */
        _sortDatasetList: function (list) {
            // currently only natural sort by name
            list.sort((a, b) => naturalSort(a.name, b.name));
            return list;
        },
        filterElements: function (elements, filterText) {
            return elements.filter((e) => this.filterElement(e, filterText));
        },
        filterElement: function (element, filterText) {
            return filterText == "" || new RegExp(filterText).test(element.name);
        },
        forwardElementSelected: function (e) {
            if (this.selectedForwardElement == null || !this.selectedForwardElement.id == e.id) {
                this.selectedForwardElement = e;
            } else {
                this.selectedForwardElement = null;
            }
            if (
                this.selectedForwardElement &&
                this.selectedReverseElement &&
                this.selectedReverseElement != this.selectedForwardElement
            ) {
                this._pair(this.selectedForwardElement, this.selectedReverseElement);
            }
        },
        reverseElementSelected: function (e) {
            if (this.selectedReverseElement == null || !this.selectedReverseElement.id == e.id) {
                this.selectedReverseElement = e;
            } else {
                this.selectedReverseElement = null;
            }
            if (
                this.selectedForwardElement &&
                this.selectedReverseElement &&
                this.selectedReverseElement != this.selectedForwardElement
            ) {
                this._pair(this.selectedForwardElement, this.selectedReverseElement);
            }
        },

        // ------------------------------------------------------------------------ pairing / unpairing
        /** create a pair from fwd and rev, removing them from unpaired, and placing the new pair in paired */
        _pair: function (fwd, rev, options) {
            options = options || {};
            var pair = this._createPair(fwd, rev, options.name);
            this.pairedElements.push(pair);
            this.removePairFromUnpaired(fwd, rev);
            if (!options.silent) {
                this.$emit("pair:new", pair);
            }
            return pair;
        },
        removePairFromUnpaired: function (fwd, rev) {
            this.workingElements.splice(this.workingElements.indexOf(rev), 1);
            this.workingElements.splice(this.workingElements.indexOf(fwd), 1);
            this.selectedForwardElement = null;
            this.selectedReverseElement = null;
        },
        /** create a pair Object from fwd and rev, adding the name attribute (will guess if not given) */
        _createPair: function (fwd, rev, name) {
            // ensure existance and don't pair something with itself
            if (!(fwd && rev) || fwd === rev) {
                throw new Error(`Bad pairing: ${[JSON.stringify(fwd), JSON.stringify(rev)]}`);
            }
            name = name || this._guessNameForPair(fwd, rev);
            return { forward: fwd, name: name, reverse: rev };
        },
        /** try to find a good pair name for the given fwd and rev datasets */
        _guessNameForPair: function (fwd, rev, removeExtensions) {
            removeExtensions = removeExtensions ? removeExtensions : this.removeExtensions;
            let fwdName = fwd.name;
            let revName = rev.name;
            const fwdNameFilter = fwdName.replace(new RegExp(this.forwardFilter), "");
            const revNameFilter = revName.replace(new RegExp(this.reverseFilter), "");
            let lcs = this._naiveStartingAndEndingLCS(fwdNameFilter, revNameFilter);
            /** remove url prefix if files were uploaded by url */
            const lastSlashIndex = lcs.lastIndexOf("/");
            if (lastSlashIndex > 0) {
                const urlprefix = lcs.slice(0, lastSlashIndex + 1);
                lcs = lcs.replace(urlprefix, "");
            }

            if (removeExtensions) {
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
        },
        clickAutopair: function () {
            // Unselect any selected elements
            this.selectedForwardElement = null;
            this.selectedReverseElement = null;
            this.autoPair();
            this.workingElements = this.workingElements.filter((e) => !this.pairedElements.includes(e));
        },
        clickUnpair: function (pair) {
            return () => this._unpair(pair);
        },
        clickClearFilters: function () {
            this.forwardFilter = "";
            this.reverseFilter = "";
        },
        splitByFilter: function () {
            var filters = [new RegExp(this.forwardFilter), new RegExp(this.reverseFilter)];
            var split = [[], []];
            this.workingElements.forEach((e) => {
                filters.forEach((filter, i) => {
                    if (filter.test(e.name)) {
                        split[i].push(e);
                    }
                });
            });
            return split;
        },
        // ------------------------------------------------------------------------ auto pairing
        /** two passes to automatically create pairs:
         *  use both simpleAutoPair, then the fn mentioned in strategy
         */
        autoPair: function (strategy) {
            var split = this.splitByFilter();
            var paired = [];
            if (this.twoPassAutopairing) {
                var simplePaired = this.autopairSimple({
                    listA: split[0],
                    listB: split[1],
                });
                paired = simplePaired ? simplePaired : paired;
                split = this.splitByFilter();
            }

            // uncomment to see printlns while running tests
            //console.debug = function(){ console.log.apply( console, arguments ); };

            // then try the remainder with something less strict
            strategy = strategy || this.strategy;
            split = this.splitByFilter();
            var pairedStrategy = strategy.call(this, {
                listA: split[0],
                listB: split[1],
            });
            paired = pairedStrategy ? paired.concat(pairedStrategy) : paired;
            return paired;
        },
        /** add a dataset to the unpaired list in it's proper order */
        _addToUnpaired: function (dataset) {
            // currently, unpaired is natural sorted by name, use binary search to find insertion point
            var binSearchSortedIndex = (low, hi) => {
                if (low === hi) {
                    return low;
                }

                var mid = Math.floor((hi - low) / 2) + low;

                var compared = naturalSort(dataset.name, this.workingElements[mid].name);

                if (compared < 0) {
                    return binSearchSortedIndex(low, mid);
                } else if (compared > 0) {
                    return binSearchSortedIndex(mid + 1, hi);
                }
                // walk the equal to find the last
                while (this.workingElements[mid] && this.workingElements[mid].name === dataset.name) {
                    mid++;
                }
                return mid;
            };

            this.workingElements.splice(binSearchSortedIndex(0, this.workingElements.length), 0, dataset);
        },
        /** unpair a pair, removing it from paired, and adding the fwd,rev datasets back into unpaired */
        _unpair: function (pair) {
            if (!pair) {
                throw new Error(`Bad pair: ${JSON.stringify(pair)}`);
            }
            this.pairedElements.splice(this.pairedElements.indexOf(pair), 1);
            this._addToUnpaired(pair.forward);
            this._addToUnpaired(pair.reverse);

            return pair;
        },
        /** unpair all paired datasets */
        unpairAll: function () {
            var pairs = [];
            while (this.pairedElements.length) {
                pairs.push(this._unpair(this.pairedElements[0], { silent: true }));
            }
        },
        // ============================================================================
        /** returns an autopair function that uses the provided options.match function */
        autoPairFnBuilder: function (options) {
            options = options || {};
            options.createPair =
                options.createPair ||
                function _defaultCreatePair(params) {
                    params = params || {};
                    var a = params.listA.splice(params.indexA, 1)[0];
                    var b = params.listB.splice(params.indexB, 1)[0];
                    var aInBIndex = params.listB.indexOf(a);
                    var bInAIndex = params.listA.indexOf(b);
                    if (aInBIndex !== -1) {
                        params.listB.splice(aInBIndex, 1);
                    }
                    if (bInAIndex !== -1) {
                        params.listA.splice(bInAIndex, 1);
                    }
                    return this._pair(a, b, { silent: true });
                };
            // compile these here outside of the loop
            var _regexps = [];
            function getRegExps() {
                if (!_regexps.length) {
                    _regexps = [new RegExp(this.forwardFilter), new RegExp(this.reverseFilter)];
                }
                return _regexps;
            }
            // mangle params as needed
            options.preprocessMatch =
                options.preprocessMatch ||
                function _defaultPreprocessMatch(params) {
                    var regexps = getRegExps.call(this);
                    return Object.assign(params, {
                        matchTo: params.matchTo.name.replace(regexps[0], ""),
                        possible: params.possible.name.replace(regexps[1], ""),
                    });
                };

            return function _strategy(params) {
                // console.debug("autopair _strategy ---------------------------");
                params = params || {};
                var listA = params.listA;
                var listB = params.listB;
                var indexA = 0;
                var indexB;

                var bestMatch = {
                    score: 0.0,
                    index: null,
                };

                var paired = [];
                //console.debug( 'params:', JSON.stringify( params, null, '  ' ) );
                // console.debug("starting list lens:", listA.length, listB.length);
                // console.debug("bestMatch (starting):", JSON.stringify(bestMatch, null, "  "));

                while (indexA < listA.length) {
                    var matchTo = listA[indexA];
                    bestMatch.score = 0.0;

                    for (indexB = 0; indexB < listB.length; indexB++) {
                        var possible = listB[indexB];
                        // console.debug(`${indexA}:${matchTo.name}`);
                        // console.debug(`${indexB}:${possible.name}`);

                        // no matching with self
                        if (listA[indexA] !== listB[indexB]) {
                            bestMatch = options.match.call(
                                this,
                                options.preprocessMatch.call(this, {
                                    matchTo: matchTo,
                                    possible: possible,
                                    index: indexB,
                                    bestMatch: bestMatch,
                                })
                            );
                            // console.debug("bestMatch:", JSON.stringify(bestMatch, null, "  "));
                            if (bestMatch.score === 1.0) {
                                // console.debug("breaking early due to perfect match");
                                break;
                            }
                        }
                    }
                    var scoreThreshold = options.scoreThreshold.call(this);
                    // console.debug("scoreThreshold:", scoreThreshold);
                    // console.debug("bestMatch.score:", bestMatch.score);

                    if (bestMatch.score >= scoreThreshold) {
                        //console.debug( 'autoPairFnBuilder.strategy', listA[ indexA ].name, listB[ bestMatch.index ].name );
                        paired.push(
                            options.createPair.call(this, {
                                listA: listA,
                                indexA: indexA,
                                listB: listB,
                                indexB: bestMatch.index,
                            })
                        );
                        //console.debug( 'list lens now:', listA.length, listB.length );
                    } else {
                        indexA += 1;
                    }
                    if (!listA.length || !listB.length) {
                        return paired;
                    }
                }
                // console.debug("paired:", JSON.stringify(paired, null, "  "));
                // console.debug("autopair _strategy ---------------------------");
                return paired;
            };
        },
        changeFilters: function (filter) {
            this.forwardFilter = this.commonFilters[filter][0];
            this.reverseFilter = this.commonFilters[filter][1];
        },
        clickedCreate: function (collectionName) {
            this.checkForDuplicates();
            if (this.state == "build") {
                this.$emit("clicked-create", this.workingElements, this.collectionName, this.hideSourceItems);
                return this.creationFn(this.pairedElements, collectionName, this.hideSourceItems)
                    .done(this.oncreate)
                    .fail(() => {
                        this.state = "error";
                    });
            }
        },
        checkForDuplicates: function () {
            var existingPairNames = {};
            this.duplicatePairNames = [];
            var valid = true;
            this.pairedElements.forEach((pair) => {
                if (Object.prototype.hasOwnProperty.call(existingPairNames, pair.name)) {
                    valid = false;
                    this.duplicatePairNames.push(pair.name);
                }
                existingPairNames[pair.name] = true;
            });
            this.state = valid ? "build" : "duplicates";
        },
        stripExtension(name) {
            return name.includes(".") ? name.substring(0, name.lastIndexOf(".")) : name;
        },
    },
};
</script>
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
            margin-left: 34px;
            margin-right: 34px;
            border: 2px solid grey;
            background: #aff1af;
            height: auto;
            span {
                display: inline-block;
                overflow: visible !important;
            }
            .forward-dataset-name {
                text-align: right;
                border-right: 1px solid grey;
                padding-right: 8px;
                &:after {
                    @extend .fas;
                    margin-left: 8px;
                    content: fa-content($fa-var-arrow-right);
                }
            }
            .pair-name-column {
                text-align: center;
                .pair-name:hover {
                    text-decoration: underline;
                }
            }
            .reverse-dataset-name {
                border-left: 1px solid grey;
                padding-left: 8px;
                &:before {
                    @extend .fas;
                    margin-right: 8px;
                    content: fa-content($fa-var-arrow-left);
                }
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
            text-align: right;
            margin-left: 32px;
        }
    }
}
.column-header {
    width: 100%;
    text-align: center;
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
    .unpair-btn {
        float: right;
        margin-top: -32px;
        width: 31px;
        height: 32px;
        //z-index: 1;
        border-color: transparent;
        //border-color: #BFBFBF;
        background: transparent;
        font-size: 120%;
        &:hover {
            border-color: #bfbfbf;
            background: #dedede;
        }
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
