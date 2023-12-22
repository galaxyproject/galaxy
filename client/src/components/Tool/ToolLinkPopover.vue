<script setup lang="ts">
import ToolLink from "./ToolLink.vue";

interface ToolLinkPopoverProps {
    target: string | Function;
    toolId?: string;
    toolVersion?: string;
}

withDefaults(defineProps<ToolLinkPopoverProps>(), {
    toolId: undefined,
    toolVersion: undefined,
});

// default boundary of scrollParent doesn't work well at all in the workflow display list
const boundary = "window";
</script>

<template>
    <b-popover v-if="toolId" :boundary="boundary" :target="target" triggers="hover">
        Tool:
        <ToolLink :tool-id="toolId" :tool-version="toolVersion || 'latest'" />
    </b-popover>
</template>
