<template>
    <div>
        <div class="alert alert-secondary" role="alert">
            <div class="float-left">Change Database/Build of all elements in collection</div>
            <div class="text-right">
                <button
                    class="save-collection-edit btn btn-primary"
                    @click="clickedSave"
                    :disabled="genome.id == databaseKey"
                >
                    {{ l("Save") }}
                </button>
            </div>
        </div>
        <b>{{ l("Database/Build: ") }}</b>
        <multiselect
            v-model="genome"
            deselect-label="Can't remove this value"
            track-by="id"
            label="text"
            :options="genomes"
            :searchable="true"
            :allow-empty="false"
        >
            {{ genome.text }}
        </multiselect>
    </div>
</template>
<script>
import Multiselect from "vue-multiselect";
export default {
    created() {},
    components: { Multiselect },
    data: function () {
        return {
            selectedGenome: {},
        };
    },
    props: {
        databaseKeyFromElements: {
            type: String,
            required: true,
        },
        genomes: {
            type: Array,
            required: true,
        },
    },
    methods: {
        clickedSave: function () {
            this.$emit("clicked-save", "dbkey", this.genome);
        },
    },
    computed: {
        genome: {
            get() {
                return this.selectedGenome;
            },
            set(element) {
                this.selectedGenome = element;
                console.log();
            },
        },
    },
    watch: {
        databaseKeyFromElements(databaseKeyFromElements) {
            this.genome = this.genomes.find((element) => element.id == this.databaseKeyFromElements);
        },
    },
};
</script>
