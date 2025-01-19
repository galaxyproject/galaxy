<template>
    <div class="h-100 w-75 mx-auto">
        <div v-for="(cell, cellIndex) of cells" :key="cellIndex">
            <CellButtonAdd :cell-index="cellIndex" @click="onClick" />
            <hr class="solid m-0" />
            <div class="d-flex my-1 mx-3">
                <span class="cell-name small text-primary">{{ cell.name }}</span>
                <CellCode :model-value="cell.content" class="ml-2" />
            </div>
            <hr class="solid m-0" />
        </div>
        <CellButtonAdd :cell-index="cells.length" @click="onClick" />
    </div>
</template>

<script setup lang="ts">
import { ref } from "vue";

import { parseMarkdown } from "@/components/Markdown/parse";

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

function onClick(cellIndex: number, cellType: string) {
    console.log([cellIndex, cellType]);
}
</script>

<style scoped>
.cell-name {
    width: 3rem;
}
</style>
