<script setup lang="ts">
import ToolHelpMarkdown from "./ToolHelpMarkdown.vue";
import ToolHelpRst from "./ToolHelpRst.vue";

defineProps<{
    format: string;
    content: string;
}>();
</script>
<template>
    <span>
        <ToolHelpMarkdown v-if="format == 'markdown'" :content="content" />
        <ToolHelpRst v-else-if="format == 'restructuredtext'" :content="content" />
        <div v-else class="form-help form-text">
            {{ content }}
        </div>
    </span>
</template>
