<template>
    <div class="pair-collection-creator">
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
            <div v-else-if="!exactlyTwoValidElements">
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
                    {{ exactlyTwoValidElementsPartOne }}
                    <a class="cancel-text" href="javascript:void(0)" role="button" @click="oncancel">
                        {{ cancelText }}
                    </a>
                    {{ exactlyTwoValidElementsPartTwo }}
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
                    :hide-source-items="hideSourceItems"
                    :suggested-name="initialSuggestedName"
                    @onUpdateHideSourceItems="onUpdateHideSourceItems"
                    @clicked-create="clickedCreate"
                    @remove-extensions-toggle="removeExtensionsToggle">
                    <template v-slot:help-content>
                        <p>
                            {{
                                l(
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
                                {{ l("Click the ") }}
                                <i data-target=".swap">
                                    {{ l("Swap") }}
                                </i>
                                {{ l("link to make your forward dataset the reverse and the reverse dataset forward") }}
                            </li>
                            <li>
                                {{ l("Click the ") }}
                                <i data-target=".cancel-create">
                                    {{ l("Cancel") }}
                                </i>
                                {{ l("button to exit the interface.") }}
                            </li>
                        </ul>
                        <br />
                        <p>
                            {{ l("Once your collection is complete, enter a ") }}
                            <i data-target=".collection-name"> {{ l("name") }}</i>
                            {{ l("and click ") }}
                            <i data-target=".create-collection">
                                {{ l("Create list") }}
                            </i>
                            {{ l(".") }}
                        </p>
                    </template>
                    <template v-slot:middle-content>
                        <div class="collection-elements-controls">
                            <a
                                class="swap"
                                href="javascript:void(0);"
                                title="l('Swap forward and reverse datasets')"
                                @click="swapButton">
                                {{ l("Swap") }}
                            </a>
                        </div>
                        <div class="collection-elements scroll-container flex-row">
                            <div
                                v-for="(element, index) in workingElements"
                                :key="element.id"
                                class="collection-element">
                                {{ index == 0 ? l("forward") : l("reverse") }}: {{ element.name }}
                            </div>
                        </div>
                    </template>
                </collection-creator>
            </div>
        </div>
    </div>
</template>

<script>
import mixin from "./common/mixin";
import STATES from "mvc/dataset/states";
import _l from "utils/localization";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);
export default {
    mixins: [mixin],
    data: function () {
        return {
            state: "build", //error
            errorText: _l("Galaxy could not be reached and may be updating.  Try again in a few minutes."),
            noElementsHeader: _l("No datasets were selected."),
            allInvalidElementsPartOne: _l("Exactly two elements needed for the collection. You may need to"),
            cancelText: _l("cancel"),
            allInvalidElementsPartTwo: _l("and reselect new elements."),
            exactlyTwoValidElementsPartOne: _l("Two (and only two) elements are needed for the pair. You may need to "),
            exactlyTwoValidElementsPartTwo: _l("and reselect new elements."),
            invalidHeader: _l("The following selections could not be included due to problems:"),
            minElements: 2,
            workingElements: [],
            invalidElements: [],
            removeExtensions: true,
            initialSuggestedName: "",
        };
    },
    computed: {
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
        exactlyTwoValidElements: function () {
            return this.workingElements.length == 2;
        },
    },
    created() {
        this._elementsSetUp();
        this.initialSuggestedName = this._guessNameForPair(
            this.workingElements[0],
            this.workingElements[1],
            this.removeExtensions
        );
    },
    methods: {
        l(str) {
            // _l conflicts private methods of Vue internals, expose as l instead
            return _l(str);
        },
        _elementsSetUp: function () {
            /** a list of invalid elements and the reasons they aren't valid */
            this.invalidElements = [];
            //TODO: handle fundamental problem of syncing DOM, views, and list here
            /** data for list in progress */
            this.workingElements = [];
            // copy initial list, sort, add ids if needed
            this.workingElements = JSON.parse(JSON.stringify(this.initialElements.slice(0)));
            this._ensureElementIds();
            this._validateElements();
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
        swapButton: function () {
            this.workingElements = [this.workingElements[1], this.workingElements[0]];
        },
        clickedCreate: function (collectionName) {
            if (this.state !== "error") {
                this.$emit("clicked-create", this.workingElements, this.collectionName, this.hideSourceItems);
                return this.creationFn(this.workingElements, collectionName, this.hideSourceItems)
                    .done(this.oncreate)
                    .fail(() => {
                        this.state = "error";
                    });
            }
        },
        /** string rep */
        toString: function () {
            return "PairCollectionCreator";
        },
        removeExtensionsToggle: function () {
            this.removeExtensions = !this.removeExtensions;
            this.initialSuggestedName = this._guessNameForPair(
                this.workingElements[0],
                this.workingElements[1],
                this.removeExtensions
            );
        },
        _guessNameForPair: function (fwd, rev, removeExtensions) {
            removeExtensions = removeExtensions ? removeExtensions : this.removeExtensions;
            var fwdName = fwd.name;
            var revName = rev.name;

            var lcs = this._naiveStartingAndEndingLCS(fwdName, revName);

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
    },
};
</script>

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
