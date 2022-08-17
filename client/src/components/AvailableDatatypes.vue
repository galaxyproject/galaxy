<script setup>
import { ref } from "vue";
import { useGetDetailedDatatypes } from "composables/datatypes";
import { useFilterObjectArray } from "composables/filter";
import DelayedInput from "components/Common/DelayedInput";

const filter = ref("");
const filterFields = ["extension"];

const { datatypes } = useGetDetailedDatatypes();
const filteredDatatypes = useFilterObjectArray(datatypes, filter, filterFields);

const fields = [
    {
        key: "extension",
    },
    {
        key: "edamFormatLabel",
        label: "EDAM Format",
    },
    {
        key: "edamDataLabel",
        label: "EDAM Data",
    },
];

const edamLink = (edamIRI) => `https://edamontology.github.io/edam-browser/#${edamIRI}`;
</script>

<template>
    <div>
        <h1>Datatypes</h1>
        <p>All Datatypes supported by this Galaxy instance. Hover over an item for more information.</p>
        <DelayedInput placeholder="filter extensions" class="mb-3" :delay="200" @change="(val) => (filter = val)" />
        <b-table striped small :items="filteredDatatypes" :fields="fields">
            <template v-slot:cell(extension)="row">
                <span v-b-tooltip.hover :title="row.item.description">
                    {{ row.item.extension }}
                </span>
            </template>

            <template v-slot:cell(edamFormatLabel)="row">
                <a
                    v-b-tooltip.hover
                    target="_blank"
                    :href="edamLink(row.item.edamFormat)"
                    :title="row.item.edamFormatDefinition">
                    {{ row.item.edamFormatLabel }}
                </a>
            </template>

            <template v-slot:cell(edamDataLabel)="row">
                <a
                    v-b-tooltip.hover
                    target="_blank"
                    :href="edamLink(row.item.edamData)"
                    :title="row.item.edamDataDefinition">
                    {{ row.item.edamDataLabel }}
                </a>
            </template>
        </b-table>
    </div>
</template>

<style scoped>
table {
    cursor: default;
}
</style>
