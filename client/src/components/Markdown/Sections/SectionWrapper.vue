<template>
    <MarkdownDefault v-if="name === 'markdown'" :content="content" />
    <MarkdownGalaxy v-else-if="name === 'galaxy'" :content="content" />
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
import MarkdownDefault from "../Sections/MarkdownDefault.vue";
import MarkdownGalaxy from "../Sections/MarkdownGalaxy.vue";
import MarkdownVega from "../Sections/MarkdownVega.vue";
import MarkdownVisualization from "../Sections/MarkdownVisualization.vue";

defineProps<{
    content: string;
    name: string;
}>();

defineEmits(["change"]);
</script>
