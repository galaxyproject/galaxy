<template>
    <div>
        <div>
            <span class="float-left h-sm">Convert all datasets to new format</span>
            <div class="text-right">
                <button
                    class="run-tool-collection-edit btn btn-primary"
                    :disabled="selectedConverter == {}"
                    @click="clickedConvert">
                    {{ l("Convert Collection") }}
                </button>
            </div>
        </div>
        <b>{{ l("Converter Tool: ") }}</b>
        <multiselect
            v-model="selectedConverter"
            deselect-label="Can't remove this value"
            track-by="name"
            label="name"
            :options="suitableConverters"
            :searchable="true"
            :allow-empty="true">
        </multiselect>
    </div>
</template>

<script>
import Multiselect from "vue-multiselect";
export default {
    components: { Multiselect },
    props: {
        suitableConverters: {
            type: Array,
            required: true,
        },
    },
    data: function () {
        return {
            selectedConverter: {},
        };
    },
    methods: {
        clickedConvert: function () {
            this.$emit("clicked-convert", this.selectedConverter);
            this.selectedConverter = {};
        },
    },
};
</script>
