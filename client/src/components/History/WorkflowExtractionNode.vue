<script setup lang="ts">
import { faFile } from "@fortawesome/free-regular-svg-icons";
import { faChevronCircleRight, faWrench } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import type { WorkflowExtractionJob } from "@/api/histories";

const props = defineProps<{
    job: WorkflowExtractionJob;
}>();
</script>

<template>
    <div class="workflow-node card">
        <div
            class="unselectable clearfix card-header py-1 px-2"
            :class="!props.job.checked ? 'node-header-disabled' : 'node-header'"
            :title="props.job.disabled_why ?? undefined">
            <FontAwesomeIcon :icon="props.job.is_fake ? faFile : faWrench" fixed-width />
            <span class="node-title">{{ props.job.tool_name ?? "Unknown" }}</span>
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
