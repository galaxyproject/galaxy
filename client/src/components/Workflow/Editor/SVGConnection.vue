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
const lineShift = 30;

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

const position = computed(() => {
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
    () =>
        stepStore.stepInputMapOver[props.connection.input.stepId] &&
        stepStore.stepInputMapOver[props.connection.input.stepId][props.connection.input.name]?.isCollection
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

const offsets = computed(() => getLineOffsets(inputIsMappedOver.value, outputIsMappedOver.value));

const paths = computed(() => {
    if (!position.value || !offsets.value) {
        return [];
    }

    const lines = [...Array(offsets.value.numOffsets).keys()].map((offsetIndex) => {
        const startOffset = offsets.value.startOffsets[offsetIndex] || 0;
        const endOffset = offsets.value.endOffsets[offsetIndex] || 0;
        return [
            [position.value!.startX, position.value!.startY + startOffset],
            [position.value!.startX + lineShift, position.value!.startY + startOffset],
            [position.value!.endX - lineShift, position.value!.endY + endOffset],
            [position.value!.endX, position.value!.endY + endOffset],
        ] as [number, number][];
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
    const _offsets = [-2 * ribbonMargin, -ribbonMargin, 0, ribbonMargin, 2 * ribbonMargin];
    let startOffsets = [0];
    let endOffsets = [0];
    let numOffsets = 1;

    if (outputIsMappedOver) {
        startOffsets = _offsets;
        numOffsets = _offsets.length;
    }
    if (inputIsMappedOver) {
        endOffsets = _offsets;
        numOffsets = _offsets.length;
    }
    return { numOffsets, startOffsets, endOffsets };
}

const lineOffsets = {
    "false-false": generateLineOffsets(false, false),
    "true-false": generateLineOffsets(true, false),
    "false-true": generateLineOffsets(false, true),
    "true-true": generateLineOffsets(true, true),
} as const;

function getLineOffsets(inputIsMappedOver?: boolean, outputIsMappedOver?: boolean) {
    return lineOffsets[`${inputIsMappedOver ?? false}-${outputIsMappedOver ?? false}`];
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
