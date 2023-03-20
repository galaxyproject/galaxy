import { getConnectionId, type Connection } from "@/stores/workflowConnectionStore";
import { computed, type Ref } from "vue";
import { useWorkflowStateStore, type TerminalPosition } from "@/stores/workflowEditorStateStore";
import { line, curveBasis } from "d3";
import { useConnectionStore } from "@/stores/workflowConnectionStore";
import { useWorkflowStepStore } from "@/stores/workflowStepStore";

let style = {
    connectionColor: "black",
    connectionColorInvalid: "red",
    optionalLineDash: [5, 3],
    ribbonMargin: 4,
    lineShift: 30,
};

const curve = line().curve(curveBasis);

function generateLineOffsets(inputIsMappedOver: boolean, outputIsMappedOver: boolean) {
    const _offsets = [-2 * style.ribbonMargin, -style.ribbonMargin, 0, style.ribbonMargin, 2 * style.ribbonMargin];
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

export function setDrawableConnectionStyle(newStyle: Partial<typeof style>) {
    style = { ...style, ...newStyle };
}

export function useDrawableConnection(connection: Connection, terminalPosition?: Ref<TerminalPosition | null>) {
    const stateStore = useWorkflowStateStore();
    const connectionStore = useConnectionStore();
    const stepStore = useWorkflowStepStore();

    const position = computed(() => {
        if (terminalPosition) {
            return terminalPosition.value;
        }

        const outputPos = stateStore.getOutputTerminalPosition(connection.output.stepId, connection.output.name);
        const inputPos = stateStore.getInputTerminalPosition(connection.input.stepId, connection.input.name);

        if (inputPos && outputPos) {
            return {
                startX: outputPos.value.startX,
                startY: outputPos.value.startY,
                endX: inputPos.value.endX,
                endY: inputPos.value.endY,
            };
        }

        return null;
    });

    const outputIsMappedOver = computed(() => stepStore.stepMapOver[connection.output.stepId]?.isCollection);
    const inputIsMappedOver = computed(
        () =>
            stepStore.stepInputMapOver[connection.input.stepId] &&
            stepStore.stepInputMapOver[connection.input.stepId][connection.input.name]?.isCollection
    );

    const outputIsOptional = computed(() => {
        return Boolean(
            stepStore.getStep(connection.output.stepId)?.when ||
                stepStore
                    .getStep(connection.output.stepId)
                    ?.outputs.find((output) => output.name === connection.output.name && output.optional)
        );
    });

    const connectionIsValid = computed(() => {
        return !connectionStore.invalidConnections[getConnectionId(connection)];
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
                [position.value!.startX + style.lineShift, position.value!.startY + startOffset],
                [position.value!.endX - style.lineShift, position.value!.endY + endOffset],
                [position.value!.endX, position.value!.endY + endOffset],
            ] as [number, number][];
        });

        return lines;
    });

    const draw = (ctx: CanvasRenderingContext2D) => {
        curve.context(ctx);
        ctx.beginPath();

        if (outputIsOptional.value) {
            ctx.setLineDash(style.optionalLineDash);
        } else {
            ctx.setLineDash([]);
        }

        if (connectionIsValid.value) {
            ctx.strokeStyle = style.connectionColor;
        } else {
            ctx.strokeStyle = style.connectionColorInvalid;
        }

        if (inputIsMappedOver.value || outputIsMappedOver.value) {
            ctx.lineWidth = 2;
        } else {
            ctx.lineWidth = 4;
        }

        paths.value.forEach((p) => curve(p));

        ctx.stroke();
    };

    return {
        draw,
    };
}
