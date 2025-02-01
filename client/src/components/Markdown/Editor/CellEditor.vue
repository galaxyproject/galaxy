<template>
    <div class="h-100 w-75 mx-auto">
        <div v-for="(cell, cellIndex) of cells" :key="cellIndex">
            <CellAdd :cell-index="cellIndex" @click="onAdd" />
            <hr class="solid m-0" />
            <CellWrapper :name="cell.name" :content="cell.content" @change="onChange(cellIndex, $event)" />
            <hr class="solid m-0" />
        </div>
        <CellAdd :cell-index="cells.length" @click="onAdd" />
    </div>
</template>

<script setup lang="ts">
import { ref } from "vue";

import { parseMarkdown } from "@/components/Markdown/parse";

import CellAdd from "./CellAdd.vue";
import CellWrapper from "./CellWrapper.vue";

interface CellType {
    name: string;
    content: string;
}

const props = defineProps<{
    markdownText: string;
}>();

const emit = defineEmits(["update"]);

const cells = ref<Array<CellType>>(parseMarkdown(props.markdownText));

function onAdd(cellIndex: number, cellType: string) {
    console.log([cellIndex, cellType]);
    onUpdate();
}

function onChange(cellIndex: number, cellContent: string) {
    const cell = cells.value?.[cellIndex];
    if (cell) {
        cell.content = cellContent;
    }
    onUpdate();
}

function onUpdate() {
    let newMarkdownText = "";
    cells.value.forEach((cell) => {
        if (cell.name === "markdown") {
            newMarkdownText += cell.content;
        } else {
            newMarkdownText += `\`\`\`${cell.name}\n` + cell.content + "\n```";
        }
        newMarkdownText += "\n\n";
    });
    emit("update", newMarkdownText);
}
</script>

<style lang="scss">
@import "theme/blue.scss";

.cell-guide {
    min-width: 5.5rem;
    max-width: 5.5rem;
}
</style>
