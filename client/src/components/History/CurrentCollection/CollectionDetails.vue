<template>
    <Details
        :name="dsc.name"
        :tags="dsc.tags"
        :writeable="writeable"
        :show-annotation="false"
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
    </Details>
</template>

<script>
import { DatasetCollection } from "components/History/model";
import Details from "components/History/Layout/Details";

export default {
    components: {
        Details,
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
