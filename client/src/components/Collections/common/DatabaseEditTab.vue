<template>
    <div>
        <div class="alert alert-secondary" role="alert">
            <div class="float-left">Change Database/Build of all elements in collection</div>
            <div class="text-right">
                <button
                    class="save-collection-edit btn btn-primary"
                    :disabled="selectedGenome.id == databaseKeyFromElements"
                    @click="clickedSave">
                    {{ l("Save") }}
                </button>
            </div>
        </div>
        <b>{{ l("Database/Build") }}: </b>
        <multiselect
            v-model="selectedGenome"
            deselect-label="Can't remove this value"
            track-by="id"
            label="text"
            :options="genomes"
            :searchable="true"
            :allow-empty="false">
            {{ selectedGenome.text }}
        </multiselect>
    </div>
</template>
<script>
import Multiselect from "vue-multiselect";

export default {
    components: { Multiselect },
    props: {
        genomes: {
            type: Array,
            required: true,
        },
        databaseKeyFromElements: {
            type: String,
            required: true,
        },
    },
    data: function () {
        return {
            selectedGenome: {},
        };
    },
    created() {
        this.selectedGenome = this.genomes.find((element) => element.id == this.databaseKeyFromElements);
    },
    methods: {
        clickedSave: function () {
            this.$emit("clicked-save", "dbkey", this.selectedGenome);
            this.selectedGenome = this.genomes.find((element) => element.id == this.databaseKeyFromElements);
        },
    },
};
</script>
