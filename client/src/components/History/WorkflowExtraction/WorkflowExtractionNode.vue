<script setup lang="ts">
import { faFile, faFolder } from "@fortawesome/free-regular-svg-icons";
import { faChevronCircleRight, faWrench } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import type { ClientWorkflowExtractionJob } from "./types";

import ToolLinkPopover from "@/components/Tool/ToolLinkPopover.vue";

const props = defineProps<{
    job: ClientWorkflowExtractionJob;
}>();

const nodeIcon = computed(() => {
    if (props.job.stepType === "tool") {
        return faWrench;
    }
    return props.job.stepType === "input_collection" ? faFolder : faFile;
});
</script>

<template>
    <div class="workflow-node card">
        <div
            class="unselectable clearfix card-header py-1 px-2"
            :class="!props.job.checked ? 'node-header-disabled' : 'node-header'">
            <FontAwesomeIcon :id="`step-icon-${props.job.id}-${props.job.tool_id}`" :icon="nodeIcon" fixed-width />
            <span class="node-title">
                <template v-if="'newName' in props.job">{{ props.job.newName }}</template>
                <template v-else>{{ props.job.tool_name }}</template>
            </span>

            <ToolLinkPopover
                v-if="props.job.tool_id && props.job.tool_version"
                :target="`step-icon-${props.job.id}-${props.job.tool_id}`"
                :tool-id="props.job.tool_id"
                :tool-version="props.job.tool_version" />
        </div>
        <div class="node-body position-relative card-body p-0 mx-2">
            <div v-for="output in props.job.outputs" :key="output.id" class="node-output">
                <span class="py-1 text-truncate">{{ output.hid }}: {{ output.name }}</span>
                <div class="output-terminal">
                    <FontAwesomeIcon class="terminal-icon" :icon="faChevronCircleRight" />
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";
@import "@/components/Workflow/Editor/nodeTerminalStyle";

.workflow-node {
    width: $workflow-node-width;
    border: solid $brand-primary 1px;
    overflow: visible;

    .node-header {
        background: $brand-primary;
        color: $white;
    }

    .node-header-disabled {
        background: $gray-500;
        color: $white;
    }

    .node-title {
        margin-left: 0.25rem;
    }

    .node-output {
        display: flex;
        position: relative;
    }

    .output-terminal {
        @include node-terminal-style(right);
        right: -1rem;
        top: 0.25rem;
    }
}
</style>
