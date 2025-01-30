<template>
    <div @mouseenter="hover = true" @mouseleave="hover = false">
        <div class="d-flex">
            <div class="cell-guide d-flex flex-column justify-content-between" :class="{ 'cell-hover': hover }">
                <CellButton title="Learn more">
                    <div v-if="VALID_TYPES.includes(name)" class="small">{{ name }}</div>
                    <div v-else class="small">unknown</div>
                </CellButton>
                <CellButton v-if="toggle" title="Collapse" @click="toggle = false">
                    <FontAwesomeIcon :icon="faAngleDoubleUp" />
                </CellButton>
                <CellButton v-else title="Expand" @click="toggle = true">
                    <FontAwesomeIcon :icon="faAngleDoubleDown" />
                </CellButton>
            </div>
            <div class="m-2 w-100">
                <MarkdownDefault v-if="name === 'markdown'" :content="content" />
                <MarkdownGalaxy v-else-if="name === 'galaxy'" :content="content" />
                <MarkdownVega v-else-if="name === 'vega'" :content="content" />
                <MarkdownVisualization
                    v-else-if="name === 'visualization'"
                    :content="content"
                    @change="$emit('change', $event)" />
                <MarkdownVisualization
                    v-else-if="name === 'vitessce'"
                    attribute="dataset_content"
                    name="vitessce"
                    :content="content" />
                <b-alert v-else variant="danger" show> This cell type `{{ name }}` is not available. </b-alert>
            </div>
        </div>
        <div v-if="toggle" class="d-flex">
            <div class="cell-guide d-flex flex-column justify-content-between" :class="{ 'cell-hover': hover }">
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
import MarkdownGalaxy from "../Sections/MarkdownGalaxy.vue";
import MarkdownVega from "../Sections/MarkdownVega.vue";
import MarkdownVisualization from "../Sections/MarkdownVisualization.vue";
import CellButton from "./CellButton.vue";
import CellCode from "./CellCode.vue";

const VALID_TYPES = ["galaxy", "markdown", "vega", "visualization", "vitessce"];

defineProps<{
    name: string;
    content: string;
}>();

defineEmits(["change"]);

const hover = ref(false);
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
</script>

<style lang="scss">
@import "theme/blue.scss";

.cell-guide {
    min-width: 5rem;
}

.cell-hover {
    background-color: $gray-100;
}
</style>
