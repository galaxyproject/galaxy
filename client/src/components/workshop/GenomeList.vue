<script setup lang="ts">
import { onMounted,ref } from "vue";

import { useFilterObjectArray } from "@/composables/filter";
import { fetcher } from "@/schema";

import DelayedInput from "@/components/Common/DelayedInput.vue";
import Heading from "@/components/Common/Heading.vue";

const fetchGenomes = fetcher.path("/api/genomes").method('get').create();
const data = ref<Array<GenomeFields>>([]);
const loading = ref(true);

const fields = [
    { label: "Name", key: "name", sortable: true },
    { label: "Identifier", key: "id", sortable: true },
];

interface GenomeFields {
    id: string;
    name: string;
}

const filter = ref("");
const filterFields: Array<keyof GenomeFields> = ["name", 'id'];
const filteredGenomes = useFilterObjectArray(data, filter, filterFields);

onMounted(async () => {
    const response = await fetchGenomes({});
    data.value = response.data.map((d) => ({
        name: d[0] ?? "",
        id: d[1] ?? "",
    }));
    loading.value = false;
});
</script>

<template>
    <div>
        <Heading h1 separator>Genomes List</Heading>
        <DelayedInput placeholder="Filter genomes" class="mb-3" :delay="200" @change="(val) => (filter = val)" />
        <b-table striped small sort-icon-left sort-by="name" :items="filteredGenomes" :fields="fields">
            <template v-slot:cell(name)="row">
                {{ row.item.name }}
            </template>
            <template v-slot:cell(id)="row">
                {{ row.item.id }}
            </template>
        </b-table>
        <p v-if="loading">Loading available genomes...</p>
    </div>
</template>
