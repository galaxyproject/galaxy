<template>
    <div>
        <div class="alert alert-secondary" role="alert">
            <div class="float-left">Change Database/Build of all elements in collection</div>
            <div class="text-right">
                <button
                    class="save-collection-edit btn btn-primary"
                    @click="clickedSave"
                    :disabled="genome.id == databaseKeyFromElements"
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
import store from "../../../store/index";

export default {
    created() {
        this.getGenomes();
    },
    components: { Multiselect },
    data: function () {
        return {
            selectedGenome: {},
            genomes: [],
        };
    },
    props: {
        databaseKeyFromElements: {
            type: String,
            required: true,
        },
    },
    methods: {
        clickedSave: function () {
            this.$emit("clicked-save", "dbkey", this.genome);
            this.selectedGenome = this.genomes.find((element) => element.id == this.databaseKeyFromElements);
            console.log("DBKFE", this.databaseKeyFromElements);
            console.log("SG", this.selectedGenome);
        },
        getGenomes: async function () {
            let genomes = store.getters.getUploadGenomes();
            if (!genomes || genomes.length == 0) {
                await store.dispatch("fetchUploadGenomes");
                genomes = store.getters.getUploadGenomes();
            }
            this.genomes = genomes;
        },
    },
    computed: {
        genome: {
            get() {
                return this.selectedGenome;
            },
            set(element) {
                this.selectedGenome = element;
            },
        },
    },
    watch: {
        //in order to have the dropdown populated with the correct genome, both databaseKeyFromElements and genomes have to be populated
        databaseKeyFromElements() {
            if (this.genomes.length > 0) {
                this.selectedGenome = this.genomes.find((element) => element.id == this.databaseKeyFromElements);
            }
        },
        genomes() {
            if (this.databaseKeyFromElements != null) {
                this.selectedGenome = this.genomes.find((element) => element.id == this.databaseKeyFromElements);
            }
        },
    },
};
</script>
