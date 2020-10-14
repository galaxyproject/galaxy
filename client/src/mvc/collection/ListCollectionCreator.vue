<template>
    <div class="list-collection-creator">
        <div v-if="noElementsSelected">
            <b-alert show variant="danger">
                {{ errorText }}
            </b-alert>
        </div>
        <div v-else>
            <div v-if="noElementsSelected">
                <b-alert show variant="danger" dismissible>
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
                <b-alert show variant="danger" dismissible>
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
                <collection-creator
                    :oncancel="oncancel"
                    @hide-original-toggle="hideOriginalsToggle"
                    @clicked-create="clickedCreate"
                >
                    <template v-slot:help-content>
                        <p>
                            {{
                                l(
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
                                {{ l("Rename elements in the list by clicking on") }}
                                <i data-target=".collection-element .name">
                                    {{ l("the existing name") }}
                                </i>
                                {{ l(".") }}
                            </li>
                            <li>
                                {{ l("Discard elements from the final created list by clicking on the ") }}
                                <i data-target=".collection-element .discard">
                                    {{ l("Discard") }}
                                </i>
                                {{ l("button.") }}
                            </li>
                            <li>
                                {{
                                    l(
                                        "Reorder the list by clicking and dragging elements. Select multiple elements by clicking on"
                                    )
                                }}
                                <i data-target=".collection-element">
                                    {{ l("them") }}
                                </i>
                                {{
                                    l(
                                        "and you can then move those selected by dragging the entire group. Deselect them by clicking them again or by clicking the"
                                    )
                                }}
                                <i data-target=".clear-selected">
                                    {{ l("Clear selected") }}
                                </i>
                                {{ l("link.") }}
                            </li>
                            <li>
                                {{ l("Click the") }}
                                <i data-target=".reset">
                                    {{ l("Start over") }}
                                </i>
                                {{ l("link to begin again as if you had just opened the interface.") }}
                            </li>
                            <li>
                                {{ l("Click the") }}
                                <i data-target=".cancel-create">
                                    {{ l("Cancel") }}
                                </i>
                                {{ l("button to exit the interface.") }}
                            </li>
                        </ul>
                        <br />
                        <p>
                            {{ l("Once your collection is complete, enter a ") }}
                            <i data-target=".collection-name">
                                {{ l("name") }}
                            </i>
                            {{ l("and click") }}
                            <i data-target=".create-collection">
                                {{ l("Create list") }}
                            </i>
                            {{ l(".") }}
                        </p>
                    </template>
                    <template v-slot:middle-content>
                        <div class="collection-elements-controls">
                            <a
                                class="reset"
                                href="javascript:void(0);"
                                role="button"
                                :title="titleUndoButton"
                                @click="reset"
                            >
                                {{ l("Start over") }}
                            </a>
                            <a
                                class="clear-selected"
                                v-if="atLeastOneDatasetIsSelected"
                                href="javascript:void(0);"
                                role="button"
                                :title="titleDeselectButton"
                                @click="clickClearAll"
                            >
                                {{ l("Clear selected") }}
                            </a>
                        </div>
                        <draggable
                            v-model="workingElements"
                            class="collection-elements scroll-container flex-row drop-zone"
                            @start="drag = true"
                            @end="drag = false"
                        >
                            <div v-if="noMoreValidDatasets">
                                <b-alert show variant="warning" dismissible>
                                    {{ discardedElementsHeader }}
                                    <a class="reset-text" href="javascript:void(0)" role="button" @click="reset">
                                        {{ startOverText }}
                                    </a>
                                    ?
                                </b-alert>
                            </div>
                            <dataset-collection-element-view
                                v-else
                                v-for="element in returnWorkingElements"
                                :key="element.id"
                                @element-is-selected="elementSelected"
                                @element-is-discarded="elementDiscarded"
                                :class="{ selected: getSelectedDatasetElems.includes(element.id) }"
                                :element="element"
                            />
                        </draggable>
                    </template>
                </collection-creator>
            </div>
        </div>
    </div>
</template>

<script>
import HDCA from "mvc/history/hdca-model";
import CollectionCreatorMixin from "mvc/collection/mixins/CollectionCreatorMixin";
import DatasetCollectionElementView from "mvc/collection/DatasetCollectionElementView";
import _l from "utils/localization";
import STATES from "mvc/dataset/states";
import "ui/hoverhighlight";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import draggable from "vuedraggable";

Vue.use(BootstrapVue);
export default {
    created() {
        this._setUpCommonSettings(this.$props);
        this._instanceSetUp();
        this._elementsSetUp();
    },
    components: { DatasetCollectionElementView, draggable },
    data: function () {
        return {
            state: "build", //error
            minElements: 1,
            elementViewClass: DatasetCollectionElementView,
            collectionClass: HDCA.HistoryDatasetCollection,
            className: "list-collection-creator collection-creator flex-row-container",
            footerSettings: {
                ".hide-originals": "hideOriginals",
            },
            titleUndoButton: _l("Undo all reordering and discards"),
            titleDeselectButton: _l("De-select all selected datasets"),
            noElementsHeader: _l("No datasets were selected"),
            discardedElementsHeader: _l("No elements left. Would you like to"),
            invalidHeader: _l("The following selections could not be included due to problems:"),
            allInvalidElementsPartOne: _l("At least one element is needed for the collection. You may need to"),
            cancelText: _l("cancel"),
            startOverText: _l("start over"),
            allInvalidElementsPartTwo: _l("and reselect new elements."),
            errorText: _l("Galaxy could not be reached and may be updating.  Try again in a few minutes."),
            workingElements: [],
            invalidElements: [],
            selectedDatasetElems: [],
        };
    },
    mixins: [CollectionCreatorMixin],
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
            default: true,
        },
        /** distance from list edge to begin autoscrolling list */
        autoscrollDist: {
            type: Number,
            required: false,
            default: 24,
        },
        /** Color passed to hoverhighlight */
        highlightClr: {
            type: String,
            required: false,
            default: "rgba( 64, 255, 255, 1.0 )",
        },
    },
    watch: {},
    computed: {
        atLeastOneDatasetIsSelected() {
            return this.selectedDatasetElems.length > 0;
        },
        getSelectedDatasetElems() {
            return this.selectedDatasetElems;
        },
        returnWorkingElements: function () {
            return this.workingElements;
        },
        noMoreValidDatasets() {
            return this.workingElements.length == 0;
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
        noElementsLeft: function () {
            return this.workingElements.length == 0;
        },
    },
    methods: {
        l(str) {
            // _l conflicts private methods of Vue internals, expose as l instead
            return _l(str);
        },
        /** set up instance vars */
        _instanceSetUp: function () {
            /** Ids of elements that have been selected by the user - to preserve over renders */
            this.selectedDatasetElems = [];
        },
        // ------------------------------------------------------------------------ process raw list
        /** set up main data */
        _elementsSetUp: function () {
            /** a list of invalid elements and the reasons they aren't valid */
            this.invalidElements = [];
            //TODO: handle fundamental problem of syncing DOM, views, and list here
            /** data for list in progress */
            this.workingElements = [];
            /** views for workingElements */
            this.elementViews = [];
            // copy initial list, sort, add ids if needed
            this.workingElements = this.initialElements.slice(0);
            this._ensureElementIds();
            this._validateElements();
            this._mangleDuplicateNames();
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
        // /** mangle duplicate names using a mac-like '(counter)' addition to any duplicates */
        _mangleDuplicateNames: function () {
            var SAFETY = 900;
            var counter = 1;
            var existingNames = {};
            this.workingElements.forEach((element) => {
                var currName = element.name;
                while (Object.prototype.hasOwnProperty.call(existingNames, currName)) {
                    currName = `${element.name} (${counter})`;
                    counter += 1;
                    if (counter >= SAFETY) {
                        throw new Error("Safety hit in while loop - thats impressive");
                    }
                }
                element.name = currName;
                existingNames[element.name] = true;
            });
        },
        elementSelected: function (e) {
            if (!this.selectedDatasetElems.includes(e.id)) {
                this.selectedDatasetElems.push(e.id);
            } else {
                this.selectedDatasetElems.splice(this.selectedDatasetElems.indexOf(e.id), 1);
            }
        },
        elementDiscarded: function (e) {
            this.$delete(this.workingElements, this.workingElements.indexOf(e));
            return this.workingElements;
        },
        clickClearAll: function () {
            this.selectedDatasetElems = [];
        },
        hideOriginalsToggle: function () {
            this.defaultHideSourceItems = !this.defaultHideSourceItems;
        },
        clickedCreate: function (collectionName) {
            if (this.state !== "error") {
                return this.creationFn(this.workingElements, collectionName, this.defaultHideSourceItems)
                    .done(this.oncreate)
                    .fail((this.state = "error"));
            }
        },
        /** reset all data to the initial state */
        reset: function () {
            this._instanceSetUp();
            this._elementsSetUp();
        },
        /** string rep */
        toString: function () {
            return "ListCollectionCreator";
        },
    },
};
</script>

<style lang="scss">
.list-collection-creator {
    // ======================================================================== list
    .footer {
        margin-top: 8px;
    }
    .main-help {
        cursor: pointer;
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
