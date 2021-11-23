<template>
    <div>
        <div v-if="loading"><b-spinner label="Loading Genomes..."></b-spinner></div>
        <div v-else>
            <multiselect
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
        genomes: {
            type: Array,
            required: true,
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
    created() {
        this.selectedGenome = this.genomes.find((genome) => genome.id == this.currentGenomeId);
    },
    methods: {
        selectGenome(genome) {
            this.$emit("update:selected-genome", genome);
        },
    },
};
</script>
