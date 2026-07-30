<script setup lang="ts">
import { faChevronDown, faChevronRight, faPencilAlt, faSync } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import WorkflowIcons from "@/components/Workflow/icons";
import type { OutdatedStep, SubworkflowInfo } from "@/stores/workflowStepStore";

/** Beyond this an expanded node grows taller than the canvas is useful, so the rest is summarized. */
const MAX_LISTED_STEPS = 12;

const props = defineProps<{
    subworkflowInfo: SubworkflowInfo;
    expanded: boolean;
    readonly?: boolean;
}>();

const emit = defineEmits<{
    (e: "update:expanded", expanded: boolean): void;
    (e: "edit"): void;
    (e: "upgrade"): void;
}>();

const steps = computed(() => props.subworkflowInfo.steps ?? []);
const listedSteps = computed(() => steps.value.slice(0, MAX_LISTED_STEPS));
const unlistedStepCount = computed(() => Math.max(0, steps.value.length - MAX_LISTED_STEPS));

/** Outdated steps of the subworkflow itself, keyed by order_index. Nested ones are counted but not listed. */
const outdatedByOrderIndex = computed(() => {
    const byOrderIndex = new Map<number, OutdatedStep>();
    for (const outdated of props.subworkflowInfo.outdated_steps ?? []) {
        if (outdated.subworkflow_path.length === 0) {
            byOrderIndex.set(outdated.order_index, outdated);
        }
    }
    return byOrderIndex;
});

const outdatedCount = computed(() => (props.subworkflowInfo.outdated_steps ?? []).length);
/** Outdated steps that sit further down, so they get counted in the badge but match no row here. */
const nestedOutdatedCount = computed(
    () =>
        (props.subworkflowInfo.outdated_steps ?? []).filter((outdated) => outdated.subworkflow_path.length > 0).length,
);
const sharedWorkflowNames = computed(() => props.subworkflowInfo.shared_workflow_names ?? []);

const outdatedTitle = computed(() => {
    const count = outdatedCount.value;
    const plural = count === 1 ? "step uses" : "steps use";
    return `${count} ${plural} an outdated tool or subworkflow version. Upgrade to update them in place.`;
});

const stepCountText = computed(() => {
    const count = steps.value.length;
    return `${count} ${count === 1 ? "step" : "steps"}`;
});

function stepIcon(type?: string | null) {
    return type ? WorkflowIcons[type as keyof typeof WorkflowIcons] : undefined;
}

function stepTitle(step: { label?: string | null; name: string }) {
    return step.label || step.name;
}
</script>

<template>
    <div class="node-subworkflow">
        <button
            class="node-subworkflow-toggle"
            :aria-expanded="expanded"
            :title="expanded ? 'Collapse subworkflow' : 'Expand subworkflow to see the steps inside it'"
            @click.prevent.stop="emit('update:expanded', !expanded)">
            <FontAwesomeIcon :icon="expanded ? faChevronDown : faChevronRight" fixed-width />
            <span>{{ stepCountText }}</span>
            <span v-if="outdatedCount > 0" v-g-tooltip.hover class="node-subworkflow-outdated" :title="outdatedTitle">
                {{ outdatedCount }} outdated
            </span>
        </button>

        <div v-if="expanded" class="node-subworkflow-body">
            <ol class="node-subworkflow-steps">
                <li
                    v-for="step in listedSteps"
                    :key="step.order_index"
                    class="node-subworkflow-step"
                    :class="{ outdated: outdatedByOrderIndex.has(step.order_index) }">
                    <i v-if="stepIcon(step.type)" :class="`fa fa-fw ${stepIcon(step.type)}`" />
                    <span class="node-subworkflow-step-title">{{ step.order_index + 1 }}: {{ stepTitle(step) }}</span>
                    <span v-if="outdatedByOrderIndex.has(step.order_index)" class="node-subworkflow-step-version">
                        {{ step.tool_version }} to {{ outdatedByOrderIndex.get(step.order_index)?.latest_version }}
                    </span>
                    <span v-else-if="step.tool_version" class="node-subworkflow-step-version">
                        {{ step.tool_version }}
                    </span>
                </li>
                <li v-if="unlistedStepCount > 0" class="node-subworkflow-step text-muted">
                    and {{ unlistedStepCount }} more
                </li>
                <li v-if="nestedOutdatedCount > 0" class="node-subworkflow-step text-muted">
                    {{ nestedOutdatedCount }} outdated further down
                </li>
            </ol>

            <p v-if="sharedWorkflowNames.length > 0" class="node-subworkflow-shared">
                Shares {{ sharedWorkflowNames.join(", ") }}, so editing or upgrading here changes
                {{ sharedWorkflowNames.length > 1 ? "those workflows" : "that workflow" }} everywhere.
            </p>

            <div v-if="!readonly" class="node-subworkflow-actions">
                <button
                    class="node-subworkflow-action"
                    title="Open this subworkflow in the editor, then come back here"
                    @click.prevent.stop="emit('edit')">
                    <FontAwesomeIcon :icon="faPencilAlt" fixed-width />
                    Edit
                </button>
                <button
                    v-if="outdatedCount > 0"
                    class="node-subworkflow-action"
                    title="Upgrade this subworkflow and the tools used inside it"
                    @click.prevent.stop="emit('upgrade')">
                    <FontAwesomeIcon :icon="faSync" fixed-width />
                    Upgrade
                </button>
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.node-subworkflow {
    font-size: $font-size-base * 0.85;
}

.node-subworkflow-toggle,
.node-subworkflow-action {
    background: none;
    border: none;
    padding: 0;
    color: inherit;
    text-align: left;
}

.node-subworkflow-toggle {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 0.25rem;
    color: $text-muted;
}

.node-subworkflow-outdated {
    margin-left: auto;
    padding: 0 0.35rem;
    border-radius: 0.5rem;
    background: $brand-warning;
    color: $black;
}

.node-subworkflow-steps {
    list-style: none;
    margin: 0;
    padding: 0 0 0 0.25rem;
}

.node-subworkflow-step {
    display: flex;
    align-items: baseline;
    gap: 0.25rem;
    white-space: nowrap;
    overflow: hidden;

    &.outdated {
        font-weight: bold;
    }
}

.node-subworkflow-step-title {
    overflow: hidden;
    text-overflow: ellipsis;
}

.node-subworkflow-step-version {
    margin-left: auto;
    color: $text-muted;
}

.node-subworkflow-shared {
    margin: 0.25rem 0;
    padding-left: 0.25rem;
    color: $text-muted;
}

.node-subworkflow-actions {
    display: flex;
    gap: 0.75rem;
    padding-left: 0.25rem;
}

.node-subworkflow-action {
    color: $brand-primary;

    &:hover {
        text-decoration: underline;
    }
}
</style>
