<template>
    <div class="paired-list-collection-creator">
        <collection-creator
            :oncancel="oncancel"
            @hide-original-toggle="hideOriginalsToggle"
            @clicked-create="clickedCreate"
            :creationFn="creationFn"
        >
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
                        {{ l("Choosing from a list of preset filters by clicking the") }}
                        <i data-target=".choose-filters-link">
                            {{ l("Choose filters link") }}
                        </i>
                        {{ "." }}
                    </li>
                    <li>
                        {{ l("Entering regular expressions to match dataset names. See:") }}
                        <a
                            href="https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Regular_Expressions"
                            target="_blank"
                        >
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
                                    {{ l("Unpaired forward") }}
                                </span>
                                <span class="title-info unpaired-info"> </span>
                            </div>
                            <div class="unpaired-filter forward-unpaired-filter float-left search-input">
                                <div class="input-group-prepend" :title="chooseFilterTitle">
                                    <button
                                        class="btn btn-outline-secondary dropdown-toggle"
                                        type="button"
                                        data-toggle="dropdown"
                                        aria-haspopup="true"
                                        aria-expanded="false"
                                    ></button>
                                    <div class="dropdown-menu">
                                        <a class="dropdown-item" @click="changeFilters('illumina')">_1</a>
                                        <a class="dropdown-item" @click="changeFilters('Rs')">_R1</a>
                                        <a class="dropdown-item" @click="changeFilters('FRs')">_F</a>
                                    </div>
                                </div>
                                <input type="text" :placeholder="filterTextPlaceholder" v-model="forwardFilter" />
                            </div>
                        </div>
                    </div>
                    <div class="paired-column flex-column no-flex column">
                        <div class="column-header">
                            <a
                                class="clear-filters-link"
                                href="javascript:void(0);"
                                role="button"
                                @click="clickClearFilters"
                            >
                                {{ l("Clear Filters") }}
                            </a>
                            <br />
                            <a class="autopair-link" href="javascript:void(0);" role="button" @click="clickAutopair">
                                {{ l("Auto-pair") }}
                            </a>
                        </div>
                    </div>
                    <div class="reverse-column flex-column column">
                        <div class="column-header">
                            <div class="column-title">
                                <span class="title">
                                    {{ l("Unpaired reverse") }}
                                </span>
                                <span class="title-info unpaired-info"></span>
                            </div>
                            <div class="unpaired-filter reverse-unpaired-filter float-left search-input search-query">
                                <div class="input-group-prepend" :title="chooseFilterTitle">
                                    <button
                                        class="btn btn-outline-secondary dropdown-toggle"
                                        type="button"
                                        data-toggle="dropdown"
                                        aria-haspopup="true"
                                        aria-expanded="false"
                                    ></button>
                                    <div class="dropdown-menu">
                                        <a class="dropdown-item" @click="changeFilters('illumina')">_2</a>
                                        <a class="dropdown-item" @click="changeFilters('Rs')">_R2</a>
                                        <a class="dropdown-item" @click="changeFilters('FRs')">_R</a>
                                    </div>
                                </div>
                                <input type="text" :placeholder="filterTextPlaceholder" v-model="reverseFilter" />
                            </div>
                        </div>
                    </div>
                </div>
                <div class="unpaired-columns flex-column-container scroll-container flex-row">
                    <div class="forward-column flex-column column">
                        <ol class="column-datasets">
                            <dataset-collection-element-view
                                v-for="element in forwardElements"
                                :key="element.id"
                                @element-is-selected="forwardElementSelected"
                                :class="{ selected: selectedForwardElement && element.id == selectedForwardElement.id }"
                                :element="element"
                            />
                        </ol>
                    </div>
                    <div class="paired-column flex-column no-flex column">
                        <ol class="column-datasets"></ol>
                    </div>
                    <div class="reverse-column flex-column column">
                        <ol class="column-datasets">
                            <dataset-collection-element-view
                                v-for="element in reverseElements"
                                :key="element.id"
                                @element-is-selected="reverseElementSelected"
                                :class="{ selected: selectedReverseElement && element.id == selectedReverseElement.id }"
                                :element="element"
                            />
                        </ol>
                    </div>
                </div>
                <div class="flexible-partition">
                    <div class="flexible-partition-drag" :title="dragToChangeTitle"></div>
                    <div class="column-header">
                        <div class="column-title paired-column-title">
                            <span class="title"></span>
                        </div>
                        <a class="unpair-all-link" href="javascript:void(0);" role="button" @click="unpairAll">
                            {{ l("Unpair all") }}
                        </a>
                    </div>
                </div>
                <div class="paired-columns flex-column-container scroll-container flex-row">
                    <ol class="column-datasets">
                        <paired-element-view
                            class="dataset paired"
                            v-for="pair in pairedElements"
                            :key="pair.id"
                            :pair="pair"
                            :unlinkFn="clickUnpair(pair)"
                        />
                    </ol>
                </div>
            </template>
        </collection-creator>
    </div>
</template>
<script>
import _l from "utils/localization";
import CollectionCreator from "./common/CollectionCreator";
import DatasetCollectionElementView from "./PairedListDatasetCollectionElementView";
import levenshteinDistance from "utils/levenshtein";
import PairedElementView from "./PairedListPairedElementView";
import STATES from "mvc/dataset/states";
import naturalSort from "utils/natural-sort";
//import { filter } from "rxjs/operators";
export default {
    created() {
        this._elementsSetUp();
        this.strategy = this.autopairLCS;
        this.filters = this.commonFilters[this.filters] || this.commonFilters[this.DEFAULT_FILTERS];
    },
    components: { CollectionCreator, DatasetCollectionElementView, PairedElementView }, //draggable?
    data: function () {
        return {
            state: "build", //error
            dragToChangeTitle: _l("Drag to change"),
            chooseFilterTitle: _l("Choose from common filters"),
            filterTextPlaceholder: _l("Filter text"),
            pairedElements: [],
            unpairedElements: [],
            commonFilters: {
                illumina: ["_1", "_2"],
                Rs: ["_R1", "_R2"],
                FRs: ["_F", "_R"],
            },
            DEFAULT_FILTERS: "illumina",
            filters: this.DEFAULT_FILTERS,
            automaticallyPair: true,
            matchPercentage: 0.9,
            twoPassAutoPairing: true,
            workingElements: [],
            forwardFilter: "",
            reverseFilter: "",
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
        };
    },
    props: {
        initialElements: {
            required: true,
            type: Array,
        },
        creationFn: {
            type: Function,
            required: true,
        },
        /** fn to call when the cancel button is clicked (scoped to this) - if falsy, no btn is displayed */
        oncancel: {
            type: Function,
            required: true,
        },
        oncreate: {
            type: Function,
            required: true,
        },
        defaultHideSourceItems: {
            type: Boolean,
            required: false,
            default: false,
        },
    },
    methods: {
        l(str) {
            // _l conflicts private methods of Vue internals, expose as l instead
            return _l(str);
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

            // copy initial list, sort, add ids if needed
            this.workingElements = this.initialElements.slice(0);
            this._ensureElementIds();
            this._validateElements();
            // this._mangleDuplicateNames();
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
            var validState = element.state === STATES.OK || STATES.NOT_READY_STATE.contains(element.state);
            if (!validState) {
                return _l("has errored, is paused, or is not accessible");
            }
            if (element.deleted || element.purged) {
                return _l("has been deleted or purged");
            }
            return null;
        },
        filterElements: function (elements, filterText) {
            return elements.filter((e) => this.filterElement(e, filterText));
        },
        filterElement: function (element, filterText) {
            return filterText == "" || element.name.toLowerCase().includes(filterText.toLowerCase());
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
            removeExtensions = removeExtensions !== undefined ? removeExtensions : this.removeExtensions;
            var fwdName = fwd.name;
            var revName = rev.name;

            var lcs = this._naiveStartingAndEndingLCS(
                fwdName.replace(new RegExp(this.filters[0]), ""),
                revName.replace(new RegExp(this.filters[1]), "")
            );

            /** remove url prefix if files were uploaded by url */
            var lastSlashIndex = lcs.lastIndexOf("/");
            if (lastSlashIndex > 0) {
                var urlprefix = lcs.slice(0, lastSlashIndex + 1);
                lcs = lcs.replace(urlprefix, "");
                fwdName = fwdName.replace(extension, "");
                revName = revName.replace(extension, "");
            }

            if (removeExtensions) {
                var lastDotIndex = lcs.lastIndexOf(".");
                if (lastDotIndex > 0) {
                    var extension = lcs.slice(lastDotIndex, lcs.length);
                    lcs = lcs.replace(extension, "");
                    fwdName = fwdName.replace(extension, "");
                    revName = revName.replace(extension, "");
                }
            }
            return lcs || `${fwdName} & ${revName}`;
        },
        /** return the concat'd longest common prefix and suffix from two strings */
        _naiveStartingAndEndingLCS: function (s1, s2) {
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
                paired = this.autopairSimple({
                    listA: split[0],
                    listB: split[1],
                });
                split = this.splitByFilter();
            }

            // uncomment to see printlns while running tests
            //this.debug = function(){ console.log.apply( console, arguments ); };

            // then try the remainder with something less strict
            strategy = strategy || this.strategy;
            split = this.splitByFilter();
            paired = paired.concat(
                strategy.call(this, {
                    listA: split[0],
                    listB: split[1],
                })
            );
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
                    _regexps = [new RegExp(this.filters[0]), new RegExp(this.filters[1])];
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
                // this.debug("autopair _strategy ---------------------------");
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
                // this.debug("starting list lens:", listA.length, listB.length);
                // this.debug("bestMatch (starting):", JSON.stringify(bestMatch, null, "  "));

                while (indexA < listA.length) {
                    var matchTo = listA[indexA];
                    bestMatch.score = 0.0;

                    for (indexB = 0; indexB < listB.length; indexB++) {
                        var possible = listB[indexB];
                        // this.debug(`${indexA}:${matchTo.name}`);
                        // this.debug(`${indexB}:${possible.name}`);

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
                            // this.debug("bestMatch:", JSON.stringify(bestMatch, null, "  "));
                            if (bestMatch.score === 1.0) {
                                // this.debug("breaking early due to perfect match");
                                break;
                            }
                        }
                    }
                    var scoreThreshold = options.scoreThreshold.call(this);
                    // this.debug("scoreThreshold:", scoreThreshold);
                    // this.debug("bestMatch.score:", bestMatch.score);

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
                // this.debug("paired:", JSON.stringify(paired, null, "  "));
                // this.debug("autopair _strategy ---------------------------");
                return paired;
            };
        },
        changeFilters: function (filter) {
            this.forwardFilter = this.commonFilters[filter][0];
            this.reverseFilter = this.commonFilters[filter][1];
        },
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
    },
};
</script>
<style scoped>
.column-headers {
    margin-bottom: 8px;
}
</style>
