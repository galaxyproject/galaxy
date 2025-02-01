<template>
    <div class="h-100 w-75 mx-auto">
        <div v-for="(cell, cellIndex) of cells" :key="cellIndex">
            <CellAdd :cell-index="cellIndex" @click="onAdd" />
            <hr class="solid m-0" />
            <CellWrapper
                :name="cell.name"
                :content="cell.content"
                @change="onChange(cellIndex, $event)"
                @clone="onClone(cellIndex)"
                @delete="onDelete(cellIndex)"
                @move-down="onMove(cellIndex, 'down')"
                @move-up="onMove(cellIndex, 'up')" />
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

// Add new cell
function onAdd(cellIndex: number, cellType: string) {
    console.log([cellIndex, cellType]);
    onUpdate();
}

// Handle cell code changes
function onChange(cellIndex: number, cellContent: string) {
    const cell = cells.value?.[cellIndex];
    if (cell) {
        cell.content = cellContent;
    }
    onUpdate();
}

// Clone cell and insert it at cellIndex + 1
function onClone(cellIndex: number) {
    const cell = cells.value?.[cellIndex];
    if (cell) {
        const newCells = [...(cells.value || [])];
        newCells.splice(cellIndex + 1, 0, { ...cell });
        cells.value = newCells;
        onUpdate();
    }
}

// Delete cell
function onDelete(cellIndex: number) {
    cells.value = cells.value.filter((_, itemIndex) => itemIndex !== cellIndex);
    onUpdate();
}

// Move cell upwards and downwards
function onMove(cellIndex: number, direction: "up" | "down") {
    if (cells.value && cells.value.length > 0) {
        const newCells = [...cells.value];
        const swapIndex = direction === "up" ? cellIndex - 1 : cellIndex + 1;
        if (swapIndex >= 0 && swapIndex < newCells.length) {
            const currentCell = newCells[cellIndex];
            const swapCell = newCells[swapIndex];
            if (currentCell && swapCell) {
                newCells[cellIndex] = { ...swapCell };
                newCells[swapIndex] = { ...currentCell };
                cells.value = newCells;
                onUpdate();
            }
        }
    }
}

// Communicate cell changes to parent
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
