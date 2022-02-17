<template>
    <div class="description">
        {{ dsc.collectionType | localize }} of {{ dsc.totalElements }}
        <b v-if="isHomogeneous">{{ homogeneousDatatype }} </b>datasets
    </div>
</template>

<script>
export default {
    props: {
        dsc: { type: Object, required: true },
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
