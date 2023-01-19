<template>
    <g :id="id" :class="ribbonClasses">
        <g v-for="svgLine in paths" :key="svgLine">
            <path class="ribbon-outer" :d="svgLine" :stroke-width="stroke.outerStroke" fill="none"></path>
            <path :class="innerClass" :d="svgLine" :stroke-width="stroke.innerStroke" fill="none"></path>
        </g>
    </g>
</template>
<script lang="ts" setup>
import { line, curveBasis } from "d3";
import { computed } from "vue";
import type { TerminalPosition } from "@/stores/workflowEditorStateStore";

const props = withDefaults(
    defineProps<{
        id?: string;
        position: TerminalPosition;
        inputIsMappedOver: boolean;
        outputIsMappedOver: boolean;
        connectionIsValid?: boolean;
        nullable?: boolean;
    }>(),
    {
        id: undefined,
        inputIsMappedOver: false,
        outputIsMappedOver: false,
        connectionIsValid: true,
        nullable: false,
    }
);

const path = line().curve(curveBasis);

const ribbonMargin = 4;
const lineShift = 30;

const stroke = computed(() => {
    let innerStroke = 4;
    let outerStroke = 6;
    if (props.outputIsMappedOver || props.inputIsMappedOver) {
        innerStroke = 1;
        outerStroke = 3;
    }
    return { innerStroke, outerStroke };
});

const ribbonClasses = computed(() => (props.nullable ? "ribbon dashed" : "ribbon"));
const innerClass = computed(() => (props.connectionIsValid ? "ribbon-inner" : "ribbon-inner ribbon-inner-invalid"));

const offsets = computed(() => {
    const _offsets = [-2 * ribbonMargin, -ribbonMargin, 0, ribbonMargin, 2 * ribbonMargin];
    let startOffsets = [0];
    let endOffsets = [0];
    let numOffsets = 1;

    if (props.outputIsMappedOver) {
        startOffsets = _offsets;
        numOffsets = _offsets.length;
    }
    if (props.inputIsMappedOver) {
        endOffsets = _offsets;
        numOffsets = _offsets.length;
    }
    return { numOffsets, startOffsets, endOffsets };
});

const paths = computed(() => {
    const lines = [...Array(offsets.value.numOffsets).keys()].map((offsetIndex) => {
        const startOffset = offsets.value.startOffsets[offsetIndex] || 0;
        const endOffset = offsets.value.endOffsets[offsetIndex] || 0;
        return [
            [props.position.startX, props.position.startY + startOffset],
            [props.position.startX + lineShift, props.position.startY + startOffset],
            [props.position.endX - lineShift, props.position.endY + endOffset],
            [props.position.endX, props.position.endY + endOffset],
        ] as [number, number][];
    });
    return lines.map((line) => path(line)!);
});
</script>
