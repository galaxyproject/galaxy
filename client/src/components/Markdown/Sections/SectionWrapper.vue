<template>
    <MarkdownDefault v-if="name === 'markdown'" :content="content" />
    <MarkdownGalaxy v-else-if="name === 'galaxy'" :content="content" :labels="labels" />
    <b-alert v-else variant="danger" show> This cell type `{{ name }}` is not available. </b-alert>
</template>

<script setup lang="ts">
import type { WorkflowLabel } from "@/components/Markdown/Editor/types";

import MarkdownDefault from "../Sections/MarkdownDefault.vue";
import MarkdownGalaxy from "../Sections/MarkdownGalaxy.vue";

defineProps<{
    content: string;
    labels?: Array<WorkflowLabel>;
    name: string;
}>();

defineEmits(["change"]);
</script>
