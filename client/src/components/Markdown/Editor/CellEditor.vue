<template>
    <div class="h-100 w-100">
        <div v-for="(cell, cellIndex) of cells" :key="cellIndex">
            <div class="border rounded m-2 p-2">
                {{ cell }}
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref } from "vue";

import { parseMarkdown } from "@/components/Markdown/parse";

const props = defineProps<{
    markdownText: string;
}>();

interface CellType {
    name: string;
    content: string;
}

const cells = ref<Array<CellType>>(parseMarkdown(props.markdownText));
</script>
