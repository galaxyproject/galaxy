<template>
    <div>
        <LoadingSpan v-if="loading" message="Loading Genomes..." />
        <multiselect
            v-if="genomes"
            v-model="selectedGenome"
            deselect-label="Can't remove this value"
            track-by="id"
            label="text"
            :options="genomes"
            :searchable="true"
            :allow-empty="false"
            @select="selectGenome"
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
        genomes: {
            type: Array,
            required: false,
            default: null,
        },
        currentGenomeId: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            selectedGenome: {},
        };
    },
    methods: {
        selectGenome(genome) {
            this.$emit("update:selected-genome", genome);
        },
    },
    watch: {
        genomes: function (val) {
            if (val) {
                this.selectedGenome = this.genomes.find((genome) => genome.id == this.currentGenomeId);
            }
        },
    },
};
</script>
