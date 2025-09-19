<script setup lang="ts">
import { curveBasis, line } from "d3";
import { computed } from "vue";

import { useWorkflowStores } from "@/composables/workflowStores";
import { getConnectionId } from "@/stores/workflowConnectionStore";
import type { TerminalPosition } from "@/stores/workflowEditorStateStore";
import type { Connection } from "@/stores/workflowStoreTypes";

interface Props {
    id: string;
    connection: Connection;
    terminalPosition?: TerminalPosition | null;
    flowing?: boolean;
    breathing?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    terminalPosition: null,
    flowing: false,
    breathing: false,
});

const ribbonMargin = 4;

const curve = line().curve(curveBasis);

const { connectionStore, stateStore, stepStore } = useWorkflowStores();

const outputPos = computed(() => {
    if (props.terminalPosition) {
        return {
            startX: props.terminalPosition.startX,
            startY: props.terminalPosition.startY,
        };
    } else {
        const pos = stateStore.getOutputTerminalPosition(props.connection.output.stepId, props.connection.output.name);
        if (pos) {
            return pos;
        } else {
            return null;
        }
    }
});

const inputPos = computed(() => {
    if (props.terminalPosition) {
        return {
            endX: props.terminalPosition.endX,
            endY: props.terminalPosition.endY,
        };
    } else {
        const pos = stateStore.getInputTerminalPosition(props.connection.input.stepId, props.connection.input.name);
        if (pos) {
            return pos;
        } else {
            return null;
        }
    }
});

const connectionPosition = computed(() => {
    if (inputPos.value && outputPos.value) {
        return {
            startX: outputPos.value.startX,
            startY: outputPos.value.startY,
            endX: inputPos.value.endX,
            endY: inputPos.value.endY,
        };
    }

    return null;
});

const outputIsMappedOver = computed(() => stepStore.stepMapOver[props.connection.output.stepId]?.isCollection);
const inputIsMappedOver = computed(
    () => stepStore.stepInputMapOver[props.connection.input.stepId]?.[props.connection.input.name]?.isCollection,
);

const outputIsOptional = computed(() => {
    return Boolean(
        stepStore.getStep(props.connection.output.stepId)?.when ||
            stepStore
                .getStep(props.connection.output.stepId)
                ?.outputs.find((output) => output.name === props.connection.output.name && output.optional),
    );
});

const connectionIsValid = computed(() => {
    return !connectionStore.invalidConnections[getConnectionId(props.connection)];
});

const lineOffsets = computed(() => getLineOffsets(inputIsMappedOver.value, outputIsMappedOver.value));

// minimum line shift
const baseLineShift = 15;

// how much the x distance influences line shift
const lineShiftGrowFactorX = 0.15;

// how much the y distance influences line shift
const lineShiftGrowFactorY = 0.08;

const lineShiftX = computed(() => {
    const position = connectionPosition.value;

    if (!position) {
        return baseLineShift;
    }

    const distanceX = Math.abs(position.endX - position.startX - baseLineShift);
    const distanceY = Math.abs(position.endY - position.startY);

    const forward = position.endX >= position.startX;

    if (forward) {
        const growX = distanceX * lineShiftGrowFactorX;
        const growY = distanceY * lineShiftGrowFactorY;

        return baseLineShift + growX + growY;
    } else {
        // reverse variant had reduced growth, but a higher base
        const growX = distanceX * lineShiftGrowFactorX * 0.5;
        const growY = distanceY * lineShiftGrowFactorY * 0.5;

        return baseLineShift * 2 + growX + growY;
    }
});

const paths = computed(() => {
    const position = connectionPosition.value;
    const offsets = lineOffsets.value;

    if (!position || !offsets) {
        return [];
    }

    const forward = position.endX >= position.startX;

    const lines = [...Array(offsets.numOffsets).keys()].map((offsetIndex) => {
        const startOffset = offsets.startOffsets[offsetIndex] || 0;
        const endOffset = offsets.endOffsets[offsetIndex] || 0;

        if (forward) {
            return [
                [position.startX, position.startY + startOffset],
                [position.startX + lineShiftX.value, position.startY + startOffset],
                [position.endX - lineShiftX.value, position.endY + endOffset],
                [position.endX, position.endY + endOffset],
            ] as [number, number][];
        } else {
            // reverse variant has two additional control points to smooth curve
            const lineShiftY = (position.endY - position.startY) / 2;

            return [
                [position.startX, position.startY + startOffset],
                [position.startX + lineShiftX.value, position.startY + startOffset],
                [position.startX + lineShiftX.value, position.startY + lineShiftY + startOffset],
                [position.endX - lineShiftX.value, position.endY - lineShiftY + endOffset],
                [position.endX - lineShiftX.value, position.endY + endOffset],
                [position.endX, position.endY + endOffset],
            ] as [number, number][];
        }
    });

    return lines.map((l) => curve(l)!);
});

// Estimate path length for animation timing on flowing connections
const estimatedPathLength = computed(() => {
    if (!props.flowing) {
        return 0;
    }

    if (!connectionPosition.value) {
        return 100;
    }

    const deltaX = connectionPosition.value.endX - connectionPosition.value.startX;
    const deltaY = connectionPosition.value.endY - connectionPosition.value.startY;
    const straightDistance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);

    // Add some extra length to account for curves
    return Math.max(100, straightDistance * 1.3);
});

const lineWidth = computed(() => {
    if (inputIsMappedOver.value || outputIsMappedOver.value) {
        return 2;
    } else {
        return 4;
    }
});

const connectionClass = computed(() => {
    const classList = ["connection"];

    if (outputIsOptional.value) {
        classList.push("optional");
    }

    if (!connectionIsValid.value) {
        classList.push("invalid");
    }

    if (props.breathing) {
        classList.push("breathing");
    }

    return classList.join(" ");
});

function generateLineOffsets(inputIsMappedOver: boolean, outputIsMappedOver: boolean) {
    const offsets = [-2 * ribbonMargin, -ribbonMargin, 0, ribbonMargin, 2 * ribbonMargin];
    let startOffsets = [0];
    let endOffsets = [0];
    let numOffsets = 1;

    if (outputIsMappedOver) {
        startOffsets = offsets;
        numOffsets = offsets.length;
    }
    if (inputIsMappedOver) {
        endOffsets = offsets;
        numOffsets = offsets.length;
    }
    return { numOffsets, startOffsets, endOffsets };
}

const lineOffsetDictionary = {
    "false-false": generateLineOffsets(false, false),
    "true-false": generateLineOffsets(true, false),
    "false-true": generateLineOffsets(false, true),
    "true-true": generateLineOffsets(true, true),
} as const;

function getLineOffsets(inputIsMappedOver?: boolean, outputIsMappedOver?: boolean) {
    return lineOffsetDictionary[`${inputIsMappedOver ?? false}-${outputIsMappedOver ?? false}`];
}

function keyForIndex(index: number) {
    return `${props.id ?? "no-key"}-${index}`;
}
</script>

<template>
    <g :id="props.id" class="workflow-editor-drawable-connection">
        <path
            v-for="(path, index) in paths"
            :key="keyForIndex(index)"
            :class="connectionClass"
            :d="path"
            :stroke-width="lineWidth"
            fill="none">
        </path>

        <template v-if="props.flowing">
            <path
                v-for="(path, index) in paths"
                :key="`particle-${keyForIndex(index)}`"
                class="connection-particle"
                :d="path"
                :stroke-width="lineWidth * 2"
                :style="{
                    '--path-length': `${estimatedPathLength}px`,
                    '--animation-duration': `${Math.max(2, estimatedPathLength / 80)}s`,
                }"
                stroke-linecap="round"
                fill="none">
            </path>
        </template>
    </g>
</template>

<style lang="scss">
@import "~bootstrap/scss/_functions.scss";
@import "theme/blue.scss";

.workflow-editor-drawable-connection {
    .connection {
        stroke: #{$brand-primary};

        &.optional {
            stroke-dasharray: 5 3;
        }

        &.invalid {
            stroke: #{$brand-warning};
        }

        &.breathing {
            animation: breathe 2s ease-in-out infinite;
        }
    }

    .connection-particle {
        stroke: white;
        stroke-dasharray: 0 calc(var(--path-length, 100px) / 2) 0 var(--path-length, 100px);
        animation: flow var(--animation-duration, 1s) linear infinite;
    }
}

@keyframes flow {
    0% {
        stroke-dashoffset: 0;
    }
    100% {
        stroke-dashoffset: calc(-2 * var(--path-length, 100px) - 8px);
    }
}

@keyframes breathe {
    0%,
    100% {
        stroke-width: var(--stroke-width, 4px);
        opacity: 0.8;
    }
    25% {
        stroke-width: calc(var(--stroke-width, 4px) * 1.2);
        opacity: 0.9;
    }
    50% {
        stroke-width: calc(var(--stroke-width, 4px) * 1.4);
        opacity: 1;
    }
    75% {
        stroke-width: calc(var(--stroke-width, 4px) * 1.2);
        opacity: 0.9;
    }
}
</style>
