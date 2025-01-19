<template>
    <div class="h-100 w-75 mx-auto">
        <div v-for="(cell, cellIndex) of cells" :key="cellIndex">
            <CellButtonAdd :cell-index="cellIndex" @click="onClick" />
            <hr class="solid m-0" />
            <div class="d-flex my-1 mx-3">
                <span class="cell-name small text-primary">{{ cell.name }}</span>
                <div class="ml-2 w-100">
                    <MarkdownDefault v-if="cell.name === 'markdown'" :content="cell.content" />
                    <MarkdownVega v-else-if="cell.name === 'vega'" :content="cell.content" />
                    <MarkdownVitessce v-else-if="cell.name === 'vitessce'" :content="cell.content" />
                    <CellCode :model-value="cell.content" :mode="getMode(cell.name)" />
                </div>
            </div>
            <hr class="solid m-0" />
        </div>
        <CellButtonAdd :cell-index="cells.length" @click="onClick" />
    </div>
</template>

<script setup lang="ts">
import { ref } from "vue";

import { parseMarkdown } from "@/components/Markdown/parse";

import MarkdownDefault from "../Sections/MarkdownDefault.vue";
import MarkdownVega from "../Sections/MarkdownVega.vue";
import MarkdownVitessce from "../Sections/MarkdownVitessce.vue";
import CellButtonAdd from "./CellButtonAdd.vue";
import CellCode from "./CellCode.vue";

const props = defineProps<{
    markdownText: string;
}>();

interface CellType {
    name: string;
    content: string;
}

const cells = ref<Array<CellType>>(parseMarkdown(props.markdownText));

function getMode(cellName: string) {
    switch (cellName) {
        case "galaxy":
            return "python";
        case "markdown":
            return "markdown";
    }
    return "json";
}

function onClick(cellIndex: number, cellType: string) {
    console.log([cellIndex, cellType]);
}
</script>

<style scoped>
.cell-name {
    width: 3rem;
}
</style>
