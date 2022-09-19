<template>
    <div>
        <h6 class="description mt-1">
            a {{ collectionLabel }} with {{ elementCount }}<b>{{ homogeneousDatatype }}</b> {{ pluralizedItem }}
        </h6>
        <CollectionProgress v-if="jobStateSummary.size != 0" :summary="jobStateSummary" />
    </div>
</template>

<script>
import CollectionProgress from "./CollectionProgress";
import { JobStateSummary } from "./JobStateSummary";

export default {
    components: { CollectionProgress },
    props: {
        jobStateSummary: { type: JobStateSummary, required: true },
        collectionType: { type: String, required: true },
        elementCount: { type: Number, required: false, default: undefined },
        elementsDatatypes: { type: Array, required: false, default: () => [] },
    },
    data() {
        return {
            labels: {
                list: "list",
                "list:paired": "list",
                "list:list": "list",
                paired: "pair",
            },
        };
    },
    computed: {
        /**@return {String} */
        collectionLabel() {
            return this.labels[this.collectionType] || "nested list";
        },
        /**@return {Boolean} */
        hasSingleElement() {
            return this.elementCount === 1;
        },
        /**@return {Boolean} */
        isHomogeneous() {
            return this.elementsDatatypes.length === 1;
        },
        /**@return {String} */
        homogeneousDatatype() {
            return this.isHomogeneous ? ` ${this.elementsDatatypes[0]}` : "";
        },
        /**@return {String} */
        pluralizedItem() {
            if (this.collectionType === "list:list") {
                return this.pluralize("list");
            }
            if (this.collectionType === "list:paired") {
                return this.pluralize("pair");
            }
            if (!Object.keys(this.labels).includes(this.collectionType)) {
                //Any other kind of nested collection
                return this.pluralize("dataset collection");
            }
            return this.pluralize("dataset");
        },
    },
    methods: {
        pluralize(word) {
            return this.hasSingleElement ? word : `${word}s`;
        },
    },
};
</script>
