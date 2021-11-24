<template>
    <div>
        <div v-if="loading"><b-spinner label="Loading data types..."></b-spinner></div>
        <div v-else>
            <multiselect
                v-model="selectedDatatype"
                deselect-label="Can't remove this value"
                track-by="id"
                label="text"
                :options="datatypes"
                :searchable="true"
                :allow-empty="false"
                @select="onSelect"
            />
        </div>
    </div>
</template>

<script>
import Multiselect from "vue-multiselect";

export default {
    components: { Multiselect },
    props: {
        loading: {
            type: Boolean,
            required: false,
        },
        datatypes: {
            type: Array,
            required: true,
        },
        currentDatatype: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            selectedDatatype: {},
        };
    },
    created() {
        this.selectedDatatype = this.datatypes.find((datatype) => datatype.id == this.currentDatatype);
    },
    methods: {
        onSelect(datatype) {
            this.$emit("update:selected-datatype", datatype);
        },
    },
};
</script>
