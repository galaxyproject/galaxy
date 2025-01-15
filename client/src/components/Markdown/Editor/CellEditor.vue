<template>
    <div class="h-100 w-100">
        <div v-for="(cell, cellIndex) of cells" :key="cellIndex">
            <CellButton>
                <FontAwesomeIcon :icon="faPlusSquare" />
            </CellButton>
            <div class="border rounded mx-2 p-2">
                {{ cell }}
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { faPlusSquare } from "@fortawesome/free-regular-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref } from "vue";

import { parseMarkdown } from "@/components/Markdown/parse";

import CellButton from "./CellButton.vue";

const props = defineProps<{
    markdownText: string;
}>();

interface CellType {
    name: string;
    content: string;
}

const cells = ref<Array<CellType>>(parseMarkdown(props.markdownText));
</script>
