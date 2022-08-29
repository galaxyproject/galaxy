<script setup>
import { ref } from "vue";
import { useDetailedDatatypes } from "composables/datatypes";
import { useFilterObjectArray } from "composables/utils/filter";
import DelayedInput from "components/Common/DelayedInput";

const filter = ref("");
const filterFields = ["extension"];

const { datatypes } = useDetailedDatatypes();
const filteredDatatypes = useFilterObjectArray(datatypes, filter, filterFields);

const fields = [
    {
        key: "extension",
        sortable: true,
    },
    {
        key: "edamFormatLabel",
        label: "EDAM Format",
        sortable: true,
    },
    {
        key: "edamDataLabel",
        label: "EDAM Data",
        sortable: true,
    },
];

const edamLink = (edamIRI) => `https://edamontology.github.io/edam-browser/#${edamIRI}`;
</script>

<template>
    <div>
        <h1>Datatypes</h1>
        <p>
            All Datatypes supported by this Galaxy instance. Hover over an item for more information. These extensions
            can be filtered by in the History, by expanding "search datasets".
        </p>
        <DelayedInput placeholder="filter extensions" class="mb-3" :delay="200" @change="(val) => (filter = val)" />
        <b-table striped small sort-icon-left sort-by="extension" :items="filteredDatatypes" :fields="fields">
            <template v-slot:cell(extension)="row">
                <a
                    v-if="row.item.descriptionUrl"
                    v-b-tooltip.hover
                    target="_blank"
                    :title="row.item.description"
                    :href="row.item.descriptionUrl">
                    {{ row.item.extension }}
                </a>
                <span v-else v-b-tooltip.hover :title="row.item.description">
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
