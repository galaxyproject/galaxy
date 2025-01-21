<template>
    <div>
        <div class="d-flex">
            <div class="cell-guide d-flex flex-column justify-content-between">
                <CellButton title="Learn more">
                    <div class="small">{{ name }}</div>
                </CellButton>
                <CellButton v-if="toggle" title="Collapse" @click="toggle = false">
                    <FontAwesomeIcon :icon="faAngleDoubleUp" />
                </CellButton>
                <CellButton v-else title="Expand" @click="toggle = true">
                    <FontAwesomeIcon :icon="faAngleDoubleDown" />
                </CellButton>
            </div>
            <div class="ml-2 w-100">
                <MarkdownDefault v-if="name === 'markdown'" :content="content" />
                <MarkdownVega v-else-if="name === 'vega'" :content="content" />
                <MarkdownVitessce v-else-if="name === 'vitessce'" :content="content" />
            </div>
        </div>
        <div v-if="toggle" class="d-flex">
            <div class="cell-guide d-flex flex-column justify-content-between">
                <CellButton title="Delete">
                    <FontAwesomeIcon :icon="faTrash" />
                </CellButton>
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
import { ref } from "vue";

import MarkdownDefault from "../Sections/MarkdownDefault.vue";
import MarkdownVega from "../Sections/MarkdownVega.vue";
import MarkdownVitessce from "../Sections/MarkdownVitessce.vue";
import CellButton from "./CellButton.vue";
import CellCode from "./CellCode.vue";

defineProps<{
    name: string;
    content: string;
}>();

defineEmits(["change"]);

const toggle = ref(true);

function getMode(cellName: string) {
    switch (cellName) {
        case "galaxy":
            return "python";
        case "markdown":
            return "markdown";
    }
    return "json";
}

function onToggle() {
    toggle.value = !toggle.value;
}
</script>
