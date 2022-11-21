<template>
    <div>
        <div>
            <span class="float-left h-sm">Change Datatype/Extension of all elements in collection</span>
            <div class="text-right">
                <button
                    class="save-datatype-edit btn btn-primary"
                    :disabled="selectedDatatype.id == currentDatatype"
                    @click="clickedSave">
                    {{ l("Save") }}
                </button>
            </div>
        </div>
        <b>{{ l("New Type") }}: </b>
        <multiselect
            v-model="selectedDatatype"
            class="datatype-dropdown"
            deselect-label="Can't remove this value"
            track-by="id"
            label="text"
            :options="datatypes"
            :searchable="true"
            :allow-empty="false">
            {{ selectedDatatype.text }}
        </multiselect>
    </div>
</template>
<script>
import Multiselect from "vue-multiselect";

export default {
    components: { Multiselect },
    props: {
        datatypes: {
            type: Array,
            required: true,
        },
        datatypeFromElements: {
            type: String,
            required: true,
        },
    },
    data: function () {
        return {
            selectedDatatype: {},
            currentDatatype: "",
        };
    },
    created() {
        this.selectedDatatype = this.datatypes.find((element) => element.id == this.datatypeFromElements);
        this.currentDatatype = this.datatypeFromElements;
    },
    methods: {
        clickedSave: function () {
            this.$emit("clicked-save", this.selectedDatatype);
            this.currentDatatype = this.selectedDatatype.id;
        },
    },
};
</script>
