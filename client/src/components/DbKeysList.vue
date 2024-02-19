<script setup lang="ts">
import { onMounted, ref } from "vue";

import { useFilterObjectArray } from "@/composables/filter";
import { fetcher } from "@/schema";

import DelayedInput from "@/components/Common/DelayedInput.vue";
import Heading from "@/components/Common/Heading.vue";

const fetchDbKeys = fetcher.path("/api/genomes").method("get").create();
const data = ref<Array<DbKeyFields>>([]);
const loading = ref(true);

const fields = [
    { label: "Subject name", key: "name", sortable: true },
    { label: "Key", key: "id", sortable: true },
];

interface DbKeyFields {
    id: string;
    name: string;
}

const filter = ref("");
const filterFields: Array<keyof DbKeyFields> = ["name", "id"];
const filteredDbKeys = useFilterObjectArray(data, filter, filterFields);

onMounted(async () => {
    const response = await fetchDbKeys({});
    data.value = response.data.map((d) => ({
        name: d[0] ?? "",
        id: d[1] ?? "",
    }));
    loading.value = false;
});
</script>

<template>
    <div>
        <Heading h1 separator>Database keys</Heading>
        <p>
            The database keys listed here link to built-in, tool-specific, reference datasets that are available on this
            server. Typically this data is related to genomes (e.g. HG19) but may also include other data types. If your
            research subject is listed here, then we have pre-built datasets/indices that can be selected as reference
            data inputs for certain tools. Please note that tool-specific reference libraries may be available without
            being listed here.
        </p>
        <DelayedInput placeholder="Filter records" class="mb-3" :delay="200" @change="(val) => (filter = val)" />
        <b-table striped small sort-icon-left sort-by="name" :items="filteredDbKeys" :fields="fields">
            <template v-slot:cell(name)="row">
                {{ row.item.name }}
            </template>
            <template v-slot:cell(id)="row">
                {{ row.item.id }}
            </template>
        </b-table>
        <p v-if="loading">Loading available data...</p>
    </div>
</template>
