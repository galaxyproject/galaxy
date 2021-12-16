<template>
    <div class="description">
        A {{ dsc.collectionType | localize }} of {{ dsc.totalElements
        }}<b v-if="isHomogeneous"> {{ homogeneousDatatype }}</b> datasets.
    </div>
</template>

<script>
import { DatasetCollection } from "../../model/DatasetCollection";

export default {
    props: {
        dsc: { type: DatasetCollection, required: true },
    },
    computed: {
        /** @return {Boolean} */
        isHomogeneous() {
            return this.dsc.isHomogeneous;
        },
        /** @return {String} */
        homogeneousDatatype() {
            return this.dsc.homogeneousDatatype;
        },
    },
};
</script>
