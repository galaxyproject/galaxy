<template>
    <div class="d-flex h-100 w-100">
        {{ markdownText }}
    </div>
</template>

<script setup lang="ts">
import { ref } from "vue";

import { parseMarkdown } from "../parse";

const props = defineProps<{
    markdownText: string;
}>();

interface CellType {
    name: string;
    content: string;
}

const cells = ref<Array<CellType>>(parseMarkdown(props.markdownText));

console.log(cells.value);
</script>
