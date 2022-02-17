<template>
    <div class="description">
        {{ dsc.collectionType | localize }} of {{ dsc.totalElements }}
        <b v-if="isHomogeneous">{{ homogeneousDatatype }} </b>datasets
    </div>
</template>

<script>
import { DatasetCollection } from "components/History/model/DatasetCollection";

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
