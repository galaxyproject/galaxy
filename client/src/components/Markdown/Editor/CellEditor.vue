<template>
    <div class="h-100 w-75 mx-auto">
        <div v-for="(cell, cellIndex) in cells" :key="cellIndex" ref="cellRefs">
            <CellAdd @click="onAdd(cellIndex, $event)" />
            <hr class="solid m-0" />
            <CellWrapper
                :cell-index="cellIndex"
                :cell-total="cells.length"
                :content="cell.content"
                :configure="cell.configure"
                :labels="labels"
                :name="cell.name"
                :toggle="cell.toggle"
                @configure="onConfigure(cellIndex)"
                @change="onChange(cellIndex, $event)"
                @clone="onClone(cellIndex)"
                @delete="onDelete(cellIndex)"
                @move="onMove(cellIndex, $event)"
                @toggle="onToggle(cellIndex)" />
            <hr class="solid m-0" />
        </div>
        <CellAdd @click="onAdd(cells.length, $event)" />
    </div>
</template>

<script setup lang="ts">
import { nextTick, ref } from "vue";

import { parseMarkdown } from "@/components/Markdown/parse";

import type { CellType, WorkflowLabel } from "./types";

import CellAdd from "./CellAdd.vue";
import CellWrapper from "./CellWrapper.vue";

const props = defineProps<{
    markdownText: string;
    labels?: Array<WorkflowLabel>;
}>();

const emit = defineEmits(["update"]);

const cells = ref<Array<CellType>>(parseCells());
const cellRefs = ref<Array<HTMLElement>>([]);

// Add new cell
function onAdd(cellIndex: number, cell: CellType) {
    const newCells = [...cells.value];
    newCells.splice(cellIndex, 0, { ...cell });
    cells.value = newCells;
    onUpdate();
    scrollToCell(cellIndex);
}

// Toggle
function onConfigure(cellIndex: number) {
    const cell = cells.value?.[cellIndex];
    if (cell) {
        cell.configure = !cell.configure;
    }
}

// Handle cell code changes
function onChange(cellIndex: number, cellContent: string) {
    const cell = cells.value?.[cellIndex];
    if (cell) {
        cell.content = cellContent;
    }
    onUpdate();
}

// Clone cell and insert it at cellIndex + 1, then scroll to it
function onClone(cellIndex: number) {
    const cell = cells.value?.[cellIndex];
    if (cell) {
        const newCells = [...cells.value];
        newCells.splice(cellIndex + 1, 0, { ...cell });
        cells.value = newCells;
        onUpdate();
        scrollToCell(cellIndex + 1);
    }
}

// Delete cell
function onDelete(cellIndex: number) {
    cells.value = cells.value.filter((_, itemIndex) => itemIndex !== cellIndex);
    onUpdate();
}

// Move cell upwards or downwards, then scroll to it
function onMove(cellIndex: number, direction: "up" | "down") {
    if (cells.value.length > 0) {
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
                scrollToCell(swapIndex);
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
            newMarkdownText += `\`\`\`${cell.name}\n${cell.content}\n\`\`\``;
        }
        newMarkdownText += "\n\n";
    });
    emit("update", newMarkdownText);
}

// Toggle
function onToggle(cellIndex: number) {
    const cell = cells.value?.[cellIndex];
    if (cell) {
        cell.toggle = !cell.toggle;
    }
}

// Parse cells
function parseCells(configure: boolean = false, toggle: boolean = false) {
    return parseMarkdown(props.markdownText).map((cell) => ({ ...cell, configure, toggle }));
}

// Scroll a specific cell into view
function scrollToCell(cellIndex: number) {
    nextTick(() => {
        const element = cellRefs.value[cellIndex];
        if (element instanceof HTMLElement) {
            element.scrollIntoView({ behavior: "smooth", block: "center" });
        }
    });
}
</script>

<style>
.cell-dropdown {
    max-height: 20rem;
    max-width: 16rem;
    min-width: 16rem;
}
</style>
