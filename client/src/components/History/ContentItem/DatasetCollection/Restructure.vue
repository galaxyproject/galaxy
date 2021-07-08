<template>
    <div>
        <b-carousel
            id="carousel-1"
            v-model="slide"
            :interval="0"
            controls
            indicators
            background="#ababab"
            style="text-shadow: 1px 1px 2px #333; text-color: black"
            @sliding-start="onSlideStart"
            @sliding-end="onSlideEnd"
        >
            <b-carousel-slide
                v-if="showOperation['unzip']"
                caption="Unzip Collection"
                text="Adaptive text for paired vs list:paired, etc..."
                img-src="static/images/tools/collection_ops/unzip.png"
            ></b-carousel-slide>
            <b-carousel-slide
                v-if="showOperation['filter_empty']"
                caption="Filter Empty"
                text="Filter empty datasets."
                img-src="static/images/tools/collection_ops/filter_empty.png"
            ></b-carousel-slide>
            <b-carousel-slide
                v-if="showOperation['filter_failed']"
                caption="Filter Failed"
                text="Filter failed datasets."
                img-src="static/images/tools/collection_ops/filter_error.png"
            ></b-carousel-slide>
            <b-carousel-slide
                v-if="showOperation['flatten']"
                caption="Flatten"
                text="Flatten nested collection into a flat list."
                img-src="static/images/tools/collection_ops/flatten.png"
            ></b-carousel-slide>
            <b-carousel-slide
                v-if="showOperation['apply_rules']"
                caption="Apply Rules"
                text="Many other advanced re-organizations are possible using the Apply Rules tool."
                img-src="https://galaxy-tests.s3.amazonaws.com/galaxy-gtn-screenshots/local/rules_apply_rules_example_4_14_apply_rules_filtered_and_nested.png"
            >
            </b-carousel-slide>
        </b-carousel>
        <div v-if="isShown('apply_rules')">
            <div>
                <b-row>
                    <b-col
                        ><b-button variant="primary">
                            <span class="fa fa-fw fa-wrench"></span>
                            Launch 'Apply Rules' on this collection</b-button
                        >
                    </b-col>
                    <b-col
                        ><b-button>
                            <span class="fa fa-fw fa-graduation-cap"></span>
                            Training Materials
                        </b-button></b-col
                    >
                </b-row>
            </div>
            <p>
                The 'Apply Rules' tool allows many sophisticated re-organizations of collections. It can modify tags,
                modify collection identifiers, filter elements, modify levels of nesting, etc..
            </p>
            <p>
                The tool has a learning curve and requires understanding collections at a deep level and to think about
                how rules can be used to re-organize them in structured ways. The training materials linked above will
                help with understanding how to setup and apply these rules.
            </p>
        </div>
        <div v-if="isShown('unzip')">
            <div>
                <b-row>
                    <b-col
                        ><b-button variant="primary">
                            <span class="fa fa-fw fa-play"></span>
                            Unzip this collection
                        </b-button></b-col
                    >
                </b-row>
            </div>
            <p v-if="isNestedList">
                This will extract forward and reverse paired elements at the base of the nested list and produce two
                nested lists - one containing the forward elements and one the reverse.
            </p>
            <p v-else-if="isList">
                This will extract forward and reverse paired elements in the list and produce two flat lists - one
                containing the forward elements and one the reverse.
            </p>
            <p v-else>This will break the paired collection into two individual datasets.</p>
            <p>
                {{ new_datasets_warning }}
            </p>
        </div>
        <div v-if="isShown('filter_empty')">
            <div>
                <b-row>
                    <b-col
                        ><b-button variant="primary">
                            <span class="fa fa-fw fa-play"></span>
                            Filter empty datasets from this collection</b-button
                        ></b-col
                    >
                </b-row>
                <p>
                    This tool takes a dataset collection and filters out empty datasets. This is useful for continuing a
                    multi-sample analysis when downstream tools require datasets to have content.
                </p>
                <p>
                    {{ new_datasets_warning }}
                </p>
            </div>
        </div>
        <div v-if="isShown('filter_failed')">
            <div>
                <b-row>
                    <b-col
                        ><b-button variant="primary">
                            <span class="fa fa-fw fa-play"></span>
                            Filter failed datasets from this collection</b-button
                        ></b-col
                    >
                </b-row>
                <p>
                    This tool takes a dataset collection and filters out datasets in the failed (red) state. This is
                    useful for continuing a multi-sample analysis when one or more of the samples fails at some point.
                </p>
                <p>
                    {{ new_datasets_warning }}
                </p>
            </div>
        </div>
        <div v-if="isShown('flatten')">
            <div>
                <b-row>
                    <b-col
                        ><b-button variant="primary">
                            <span class="fa fa-fw fa-play"></span>
                            Flatten collection</b-button
                        ></b-col
                    >
                    <b-col
                        ><b-button>
                            <span class="fa fa-fw fa-wrench"></span>
                            Launch Flatten collection tool</b-button
                        ></b-col
                    >
                </b-row>
                <p>
                    This tool takes nested collections and produces a flat list from the inputs. It effectively
                    "flattens" the hierarchy.
                </p>
                <p v-if="isPaired">
                    This tool will remove the paired structure from your collection and produce a simple "list"
                    collection.
                </p>
                <p v-else>
                    This tool will remove the nested list structure from your collection and produce a simple "list"
                    collection.
                </p>
                <p>
                    The collection identifiers are merged together using "_" as default. To combine identifiers in other
                    ways, launch the tool using the second button above and tweak this setting.
                </p>
                <p>
                    {{ new_datasets_warning }}
                </p>
            </div>
        </div>
    </div>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { DatasetCollection } from "../../model/DatasetCollection";

Vue.use(BootstrapVue);
export default {
    data() {
        return {
            slide: 0,
            sliding: null,
            rules: false,
            unzip: false,
            showOperation: {},
            operationIndex: {},
        };
    },
    props: {
        collection: { type: DatasetCollection, required: true },
    },
    computed: {
        isPair() {
            return this.collection.collection_type == "paired";
        },
        isPaired() {
            return this.collection.collection_type.indexOf("paired") >= 0;
        },
        isList() {
            return this.collection.collection_type.indexOf("list") >= 0;
        },
        isNestedList() {
            return this.collection.collection_type.indexOf("list:list") >= 0;
        },
        isFlatList() {
            return this.collection.collection_type == "list";
        },
        new_datasets_warning() {
            return "This tool will create new history datasets from your collection but your quota usage will not increase.";
        },
        unzipCaption() {
            if (this.isList) {
                return "Unzip list of paired collections into forward and reverse unpaired lists.";
            } else {
                return "Unzip dataset pair into forward and reverse pair.";
            }
        },
    },
    created() {
        if (!this.isPaired) {
            this.showOperation["unzip"] = false;
        } else {
            this.showOperation["unzip"] = true;
        }
        if (this.isList && !this.isFlatList) {
            this.showOperation["flatten"] = true;
        } else {
            this.showOperation["flatten"] = false;
        }
        this.showOperation["apply_rules"] = true;
        this.showOperation["filter_empty"] = true;
        this.showOperation["filter_failed"] = true;

        let index = 0;
        for (const name of ["unzip", "filter_empty", "filter_failed", "flatten", "apply_rules"]) {
            if (this.showOperation[name]) {
                this.operationIndex[name] = index++;
            } else {
                this.operationIndex[name] = -1;
            }
        }
    },
    methods: {
        onSlideStart(slide) {
            this.sliding = true;
        },
        onSlideEnd(slide) {
            this.sliding = false;
            console.log("slide is " + this.slide);
        },
        isShown(tool) {
            console.log(this.slide);
            console.log(this.operationIndex[tool]);
            return this.slide == this.operationIndex[tool];
        },
    },
};
</script>
