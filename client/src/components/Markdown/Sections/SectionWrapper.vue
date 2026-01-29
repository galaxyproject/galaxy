<template>
    <MarkdownDefault v-if="name === 'markdown'" :content="content" />
    <MarkdownGalaxy v-else-if="name === 'galaxy'" :content="content" :labels="labels" />
    <MarkdownVega v-else-if="name === 'vega'" :content="content" />
    <MarkdownVisualization v-else-if="name === 'visualization'" :content="content" @change="$emit('change', $event)" />
    <MarkdownVitessce v-else-if="name === 'vitessce'" :content="content" />
    <BAlert v-else variant="danger" show> This cell type `{{ name }}` is not available. </BAlert>
</template>

<script setup lang="ts">
import { BAlert } from "bootstrap-vue";

import type { WorkflowLabel } from "@/components/Markdown/Editor/types";

import MarkdownDefault from "./MarkdownDefault.vue";
import MarkdownGalaxy from "./MarkdownGalaxy.vue";
import MarkdownVega from "./MarkdownVega.vue";
import MarkdownVisualization from "./MarkdownVisualization.vue";
import MarkdownVitessce from "./MarkdownVitessce.vue";

defineProps<{
    content: string;
    labels?: Array<WorkflowLabel>;
    name: string;
}>();

defineEmits(["change"]);
</script>
