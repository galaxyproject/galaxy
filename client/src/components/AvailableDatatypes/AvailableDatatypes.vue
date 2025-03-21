<script setup lang="ts">
import { ref } from "vue";

import { type DetailedDatatypes, useDetailedDatatypes } from "@/composables/datatypes";
import { useFilterObjectArray } from "@/composables/filter";

import DelayedInput from "@/components/Common/DelayedInput.vue";

const filter = ref("");
const filterFields: Array<keyof DetailedDatatypes> = ["extension"];

const { datatypes } = useDetailedDatatypes();
const filteredDatatypes = useFilterObjectArray(datatypes, filter, filterFields);

const fields = [
    {
        key: "extension",
        sortable: true,
    },
    {
        key: "edamFormatLabel",
        label: "EDAM 格式",
        sortable: true,
    },
    {
        key: "edamDataLabel",
        label: "EDAM 数据",
        sortable: true,
    },
];

const edamLink = (edamIRI: string) => `https://edamontology.github.io/edam-browser/#${edamIRI}`;
</script>

<template>
    <div>
        <h1>数据类型</h1>
        <p>
            本 Galaxy 实例支持的所有数据类型。将鼠标悬停在项目上查看更多信息。这些扩展可以在历史记录中进行过滤，通过展开“搜索数据集”。
        </p>
        <DelayedInput placeholder="过滤扩展" class="mb-3" :delay="200" @change="(val) => (filter = val)" />
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
