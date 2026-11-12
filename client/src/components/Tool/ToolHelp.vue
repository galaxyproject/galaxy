<script setup lang="ts">
import ToolHelpMarkdown from "./ToolHelpMarkdown.vue";
import ToolHelpRst from "./ToolHelpRst.vue";

defineProps<{
    format: string;
    content: string;
    toolId?: string;
    toolVersion?: string;
}>();
</script>
<template>
    <span>
        <ToolHelpMarkdown
            v-if="format == 'markdown'"
            :content="content"
            :tool-id="toolId"
            :tool-version="toolVersion" />
        <ToolHelpRst
            v-else-if="format == 'restructuredtext'"
            :content="content"
            :tool-id="toolId"
            :tool-version="toolVersion" />
        <div v-else class="form-help form-text">
            {{ content }}
        </div>
    </span>
</template>
