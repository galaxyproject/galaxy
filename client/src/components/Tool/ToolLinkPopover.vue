<script setup lang="ts">
import localize from "@/utils/localization";

import ToolLink from "./ToolLink.vue";
import GPopover from "@/components/BaseComponents/GPopover.vue";

interface ToolLinkPopoverProps {
    target: string | (() => any);
    /** The target is a button or link, so the popover can be a dialog that Tab from it enters */
    interactive?: boolean;
    toolId?: string;
    toolVersion?: string;
}

withDefaults(defineProps<ToolLinkPopoverProps>(), {
    interactive: false,
    toolId: undefined,
    toolVersion: undefined,
});

// default boundary of scrollParent doesn't work well at all in the workflow display list
const boundary = "window";
</script>

<template>
    <GPopover
        v-if="toolId"
        :interactive="interactive"
        :aria-label="localize('Tool')"
        :boundary="boundary"
        :target="target"
        triggers="hover">
        Tool:
        <ToolLink :tool-id="toolId" :tool-version="toolVersion || 'latest'" />
    </GPopover>
</template>
