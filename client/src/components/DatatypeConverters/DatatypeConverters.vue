<script setup lang="ts">
import type { FetchReturnType } from "openapi-typescript-fetch";
import { onMounted, ref } from "vue";

import { useFilterObjectArray } from "@/composables/filter";
import { fetcher } from "@/schema";

import DelayedInput from "@/components/Common/DelayedInput.vue";
import Heading from "@/components/Common/Heading.vue";

const fetchConverters = fetcher.path("/api/datatypes/converters").method("get").create();
const data = ref<FetchReturnType<typeof fetchConverters>>([]);
const filterText = ref("");
const filterFields: Array<keyof (typeof data.value)[0]> = ["source", "target", "tool_id"];

onMounted(async () => {
    const response = await fetchConverters({});
    data.value = response.data;
});

const displayedData = useFilterObjectArray(data, filterText, filterFields);

const fields = [
    {
        key: "source",
        sortable: true,
    },
    {
        key: "target",
        sortable: true,
    },
    {
        key: "tool_id",
        label: "Tool ID",
        sortable: true,
    },
];
</script>

<template>
    <div class="genome-list">
        <Heading h1 separator>Datatype Converter Listing</Heading>

        <DelayedInput placeholder="filter converters" class="mb-3" :delay="200" @change="(val) => (filterText = val)" />

        <b-table striped small sort-icon-left sort-by="tool_id" :items="displayedData" :fields="fields">
            <template v-slot:cell(source)="row">
                {{ row.item.source }}
            </template>

            <template v-slot:cell(target)="row">
                {{ row.item.target }}
            </template>

            <template v-slot:cell(tool_id)="row">
                {{ row.item.tool_id }}
            </template>
        </b-table>
    </div>
</template>
