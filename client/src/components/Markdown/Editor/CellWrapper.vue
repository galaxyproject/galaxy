<template>
    <div>
        <div class="d-flex my-1 mx-2">
            <div class="d-flex flex-column justify-content-between">
                <div class="cell-guide small text-primary">
                    {{ name }}
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
                <MarkdownDefault v-if="name === 'markdown'" :content="content" />
                <MarkdownVega v-else-if="name === 'vega'" :content="content" />
                <MarkdownVitessce v-else-if="name === 'vitessce'" :content="content" />
            </div>
        </div>
        <div class="d-flex my-1 mx-3">
            <div class="cell-guide d-flex flex-column justify-content-between">
                <b-button v-b-tooltip.right class="border-0 p-0 m-0" title="Delete" variant="outline-primary">
                    <FontAwesomeIcon :icon="faTrash" />
                </b-button>
            </div>
            <div class="ml-2 w-100">
                <CellCode :value="content" :mode="getMode(name)" @change="$emit('change', $event)" />
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { faAngleDoubleDown, faAngleDoubleUp, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import MarkdownDefault from "../Sections/MarkdownDefault.vue";
import MarkdownVega from "../Sections/MarkdownVega.vue";
import MarkdownVitessce from "../Sections/MarkdownVitessce.vue";
import CellCode from "./CellCode.vue";

defineProps<{
    name: string;
    content: string;
}>();

defineEmits(["change"]);

function getMode(cellName: string) {
    switch (cellName) {
        case "galaxy":
            return "python";
        case "markdown":
            return "markdown";
    }
    return "json";
}
</script>
