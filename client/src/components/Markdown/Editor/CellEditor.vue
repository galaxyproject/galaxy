<template>
    <div class="h-100 w-75 mx-auto">
        <div v-for="(cell, cellIndex) of cells" :key="cellIndex">
            <CellButtonAdd :cell-index="cellIndex" @click="onAdd" />
            <hr class="solid m-0" />
            <div class="d-flex my-1 mx-3">
                <div class="d-flex flex-column justify-content-between">
                    <div class="cell-name small text-primary">
                        {{ cell.name }}
                    </div>
                    <div
                        v-b-tooltip.right
                        role="button"
                        tabindex="0"
                        class="d-inline text-muted cursor-pointer mt-4 align-self-end"
                        title="Expand to Edit">
                        <FontAwesomeIcon class="text-primary" :icon="faAngleDoubleDown" />
                        <FontAwesomeIcon class="text-primary" :icon="faAngleDoubleUp" />
                    </div>
                </div>
                <div class="ml-2 w-100">
                    <MarkdownDefault v-if="cell.name === 'markdown'" :content="cell.content" />
                    <MarkdownVega v-else-if="cell.name === 'vega'" :content="cell.content" />
                    <MarkdownVitessce v-else-if="cell.name === 'vitessce'" :content="cell.content" />
                </div>
            </div>
            <div class="d-flex my-1 mx-3">
                <div class="cell-name d-flex flex-column justify-content-between">
                    <div
                        v-b-tooltip.right
                        role="button"
                        tabindex="0"
                        class="d-inline text-muted cursor-pointer mt-4 align-self-end"
                        title="Insert new Cell">
                        <FontAwesomeIcon class="text-primary" :icon="faTrash" />
                    </div>
                </div>
                <div class="ml-2 w-100">
                    <CellCode :value="cell.content" :mode="getMode(cell.name)" @change="onChange(cellIndex, $event)" />
                </div>
            </div>
            <hr class="solid m-0" />
        </div>
        <CellButtonAdd :cell-index="cells.length" @click="onAdd" />
    </div>
</template>

<script setup lang="ts">
import { ref } from "vue";

import { parseMarkdown } from "@/components/Markdown/parse";

import { faTrash, faAngleDoubleDown, faAngleDoubleUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import MarkdownDefault from "../Sections/MarkdownDefault.vue";
import MarkdownVega from "../Sections/MarkdownVega.vue";
import MarkdownVitessce from "../Sections/MarkdownVitessce.vue";
import CellButtonAdd from "./CellButtonAdd.vue";
import CellCode from "./CellCode.vue";

interface CellType {
    name: string;
    content: string;
}

const props = defineProps<{
    markdownText: string;
}>();

const emit = defineEmits(["update"]);

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

<style scoped>
.cell-name {
    width: 3rem;
}
</style>
