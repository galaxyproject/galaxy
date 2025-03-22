<template>
    <MarkdownDefault v-if="name === 'markdown'" :content="content" />
    <MarkdownGalaxy v-else-if="name === 'galaxy'" :content="content" :labels="labels" />
    <MarkdownVega v-else-if="name === 'vega'" :content="content" />
    <MarkdownVisualization v-else-if="name === 'visualization'" :content="content" @change="$emit('change', $event)" />
    <MarkdownVisualization
        v-else-if="name === 'vitessce'"
        attribute="dataset_content"
        name="vitessce"
        :content="content" />
    <b-alert v-else variant="danger" show> This cell type `{{ name }}` is not available. </b-alert>
</template>

<script setup lang="ts">
import type { WorkflowLabel } from "@/components/Markdown/Editor/types";

import MarkdownDefault from "./MarkdownDefault.vue";
import MarkdownGalaxy from "./MarkdownGalaxy.vue";
import MarkdownVega from "./MarkdownVega.vue";
import MarkdownVisualization from "./MarkdownVisualization.vue";

defineProps<{
    content: string;
    labels?: Array<WorkflowLabel>;
    name: string;
}>();

defineEmits(["change"]);
</script>
