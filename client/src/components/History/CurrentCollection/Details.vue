<template>
    <HeaderDetails
        :name="dsc.name"
        :annotation="dsc.annotation"
        :tags="dsc.tags"
        :writeable="writeable"
        @save="$emit('update:dsc', $event)">
        <template v-slot:name>
            <h3 data-description="collection name display">{{ dsc.name || "(Collection Name)" }}</h3>
            <div class="mt-1">
                <div class="description">
                    {{ dsc.collectionType | localize }} of {{ dsc.totalElements }}
                    <b v-if="isHomogeneous">{{ homogeneousDatatype }} </b>datasets
                </div>
            </div>
        </template>
    </HeaderDetails>
</template>

<script>
import { DatasetCollection } from "components/History/model";
import HeaderDetails from "components/History/HeaderDetails";

export default {
    components: {
        HeaderDetails,
    },
    props: {
        dsc: { type: Object, required: true },
        writeable: { type: Boolean, required: true },
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
