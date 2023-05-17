<script setup lang="ts">
import { line, curveBasis } from "d3";
import { computed, type PropType } from "vue";

import { getConnectionId, type Connection } from "@/stores/workflowConnectionStore";
import { useWorkflowStateStore, type TerminalPosition } from "@/stores/workflowEditorStateStore";
import { useConnectionStore } from "@/stores/workflowConnectionStore";
import { useWorkflowStepStore } from "@/stores/workflowStepStore";

const props = defineProps({
    id: String,
    connection: {
        type: Object as PropType<Connection>,
        required: true,
    },
    terminalPosition: {
        type: Object as PropType<TerminalPosition | null>,
        default: null,
    },
});

const ribbonMargin = 4;

const curve = line().curve(curveBasis);

const stateStore = useWorkflowStateStore();
const connectionStore = useConnectionStore();
const stepStore = useWorkflowStepStore();

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
    () => stepStore.stepInputMapOver[props.connection.input.stepId]?.[props.connection.input.name]?.isCollection
);

const outputIsOptional = computed(() => {
    return Boolean(
        stepStore.getStep(props.connection.output.stepId)?.when ||
            stepStore
                .getStep(props.connection.output.stepId)
                ?.outputs.find((output) => output.name === props.connection.output.name && output.optional)
    );
});

const connectionIsValid = computed(() => {
    return !connectionStore.invalidConnections[getConnectionId(props.connection)];
});

const lineOffsets = computed(() => getLineOffsets(inputIsMappedOver.value, outputIsMappedOver.value));

const baseLineShift = 15;
const lineShiftGrowFactorX = 0.15;
const lineShiftGrowFactorY = 0.1;
const lineShiftX = computed(() => {
    const position = connectionPosition.value;

    if (!position) {
        return baseLineShift;
    }

    const distanceX = position.endX - position.startX;
    const distanceY = Math.abs(position.endY - position.startY);

    const adjustedDistanceX = Math.max(distanceX - baseLineShift, 0);

    const forward = position.endX >= position.startX;

    if (forward) {
        const growX = adjustedDistanceX * lineShiftGrowFactorX;
        const growY = distanceY * lineShiftGrowFactorY;

        return baseLineShift + growX + growY;
    } else {
        const growX = adjustedDistanceX * lineShiftGrowFactorX * 0.5;
        const growY = distanceY * lineShiftGrowFactorY * 0.5;

        return baseLineShift * 2 + growX + growY;
    }
});

const lineShiftY = computed(() => {
    const position = connectionPosition.value;

    if (!position) {
        return 0;
    }

    const distanceY = position.endY - position.startY;
    return distanceY / 2;
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
            return [
                [position.startX, position.startY + startOffset],
                [position.startX + lineShiftX.value, position.startY + startOffset],
                [position.startX + lineShiftX.value, position.startY + lineShiftY.value + startOffset],
                [position.endX - lineShiftX.value, position.endY - lineShiftY.value + endOffset],
                [position.endX - lineShiftX.value, position.endY + endOffset],
                [position.endX, position.endY + endOffset],
            ] as [number, number][];
        }
    });

    return lines.map((l) => curve(l)!);
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
    }
}
</style>
