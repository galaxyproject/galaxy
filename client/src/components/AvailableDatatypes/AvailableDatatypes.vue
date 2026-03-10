<script setup lang="ts">
import { ref } from "vue";

import type { TableField } from "@/components/Common/GTable.types";
import { type DetailedDatatypes, useDetailedDatatypes } from "@/composables/datatypes";
import { useFilterObjectArray } from "@/composables/filter";

import GLink from "@/components/BaseComponents/GLink.vue";
import DelayedInput from "@/components/Common/DelayedInput.vue";
import GTable from "@/components/Common/GTable.vue";

const filter = ref("");
const filterFields: Array<keyof DetailedDatatypes> = ["extension"];

const { datatypes } = useDetailedDatatypes();
const filteredDatatypes = useFilterObjectArray(datatypes, filter, filterFields);

const fields: TableField[] = [
    {
        key: "extension",
        label: "Extension",
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

const edamLink = (edamIRI: string) => `https://edamontology.github.io/edam-browser/#${edamIRI}`;
</script>

<template>
    <div>
        <h1>Datatypes</h1>
        <p>
            All Datatypes supported by this Galaxy instance. Hover over an item for more information. These extensions
            can be filtered by in the History, by expanding "search datasets".
        </p>

        <DelayedInput placeholder="filter extensions" class="mb-3" :delay="200" @change="(val) => (filter = val)" />

        <GTable compact show-empty striped sort-by="extension" :fields="fields" :items="filteredDatatypes">
            <template v-slot:cell(extension)="{ item }">
                <GLink
                    v-if="item.descriptionUrl"
                    tooltip
                    target="_blank"
                    :title="item.description"
                    :href="item.descriptionUrl">
                    {{ item.extension }}
                </GLink>
                <span v-else v-b-tooltip.hover :title="item.description">
                    {{ item.extension }}
                </span>
            </template>

            <template v-slot:cell(edamFormatLabel)="{ item }">
                <GLink tooltip target="_blank" :href="edamLink(item.edamFormat)" :title="item.edamFormatDefinition">
                    {{ item.edamFormatLabel }}
                </GLink>
            </template>

            <template v-slot:cell(edamDataLabel)="{ item }">
                <GLink tooltip target="_blank" :href="edamLink(item.edamData)" :title="item.edamDataDefinition">
                    {{ item.edamDataLabel }}
                </GLink>
            </template>
        </GTable>
    </div>
</template>
