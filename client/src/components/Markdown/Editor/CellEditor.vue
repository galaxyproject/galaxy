<template>
    <div class="h-100 w-100">
        <div v-for="(cell, cellIndex) of cells" :key="cellIndex">
            <CellButtonAdd :cell-index="cellIndex" @click="onClick" />
            <div class="cell-card d-flex flex-column border rounded mx-3">
                <div class="cell-card-header rounded-top p-1 small text-primary">{{ cell.name }}</div>
                <div class="p-2">{{ cell.content }}</div>
            </div>
        </div>
        <CellButtonAdd :cell-index="cells.length" @click="onClick" />
    </div>
</template>

<script setup lang="ts">
import { ref } from "vue";

import { parseMarkdown } from "@/components/Markdown/parse";

import CellButtonAdd from "./CellButtonAdd.vue";

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

<style lang="scss">
@import "theme/blue.scss";

.cell-card {
    .cell-card-header {
        //background: $brand-primary;
        //color: $white;
    }
}
</style>
