<template>
    <div>
        <LoadingSpan v-if="loading" message="Loading data types..." />
        <multiselect
            v-if="datatypes"
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
</template>

<script>
import Multiselect from "vue-multiselect";
import LoadingSpan from "components/LoadingSpan";

export default {
    components: {
        Multiselect,
        LoadingSpan,
    },
    props: {
        loading: {
            type: Boolean,
            required: false,
        },
        datatypes: {
            type: Array,
            required: false,
            default: null,
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
    methods: {
        onSelect(datatype) {
            this.$emit("update:selected-datatype", datatype);
        },
    },
    watch: {
        datatypes: function (val) {
            if (val) {
                this.selectedDatatype = this.datatypes.find((datatype) => datatype.id == this.currentDatatype);
            }
        },
    },
};
</script>
