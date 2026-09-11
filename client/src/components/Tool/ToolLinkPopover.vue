<script setup lang="ts">
import ToolLink from "./ToolLink.vue";
import GPopover from "@/components/BaseComponents/GPopover.vue";

interface ToolLinkPopoverProps {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    target: string | (() => any);
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
    <GPopover v-if="toolId" :boundary="boundary" :target="target" triggers="hover">
        Tool:
        <ToolLink :tool-id="toolId" :tool-version="toolVersion || 'latest'" />
    </GPopover>
</template>
