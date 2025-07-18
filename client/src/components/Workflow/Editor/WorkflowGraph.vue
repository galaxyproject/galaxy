<script setup lang="ts">
import { useElementBounding, useScroll } from "@vueuse/core";
import { storeToRefs } from "pinia";
import { computed, type PropType, provide, reactive, type Ref, ref, watch, watchEffect } from "vue";

import { DatatypesMapperModel } from "@/components/Datatypes/model";
import { useWorkflowStores } from "@/composables/workflowStores";
import type { TerminalPosition, XYPosition } from "@/stores/workflowEditorStateStore";
import type { Step } from "@/stores/workflowStepStore";
import { assertDefined } from "@/utils/assertions";

import { useD3Zoom } from "./composables/d3Zoom";
import { useViewportBoundingBox } from "./composables/viewportBoundingBox";
import { useWorkflowBoundingBox } from "./composables/workflowBoundingBox";
import type { Rectangle, Vector } from "./modules/geometry";
import type { OutputTerminals } from "./modules/terminals";
import { maxZoom, minZoom } from "./modules/zoomLevels";

import AdaptiveGrid from "./AdaptiveGrid.vue";
import WorkflowComment from "./Comments/WorkflowComment.vue";
import BoxSelectPreview from "./Tools/BoxSelectPreview.vue";
import InputCatcher from "./Tools/InputCatcher.vue";
import ToolBar from "./Tools/ToolBar.vue";
import AreaHighlight from "@/components/Workflow/Editor/AreaHighlight.vue";
import WorkflowNode from "@/components/Workflow/Editor/Node.vue";
import WorkflowEdges from "@/components/Workflow/Editor/WorkflowEdges.vue";
import WorkflowMinimap from "@/components/Workflow/Editor/WorkflowMinimap.vue";
import ZoomControl from "@/components/Workflow/Editor/ZoomControl.vue";

const emit = defineEmits(["transform", "graph-offset", "onRemove", "scrollTo", "stepClicked"]);
const props = defineProps({
    steps: { type: Object as PropType<{ [index: string]: Step }>, required: true },
    datatypesMapper: { type: DatatypesMapperModel, required: true },
    highlightId: { type: Number as PropType<number | null>, default: null },
    scrollToId: { type: Number as PropType<number | null>, default: null },
    readonly: { type: Boolean, default: false },
    initialPosition: { type: Object as PropType<{ x: number; y: number }>, default: () => ({ x: 50, y: 20 }) },
    isInvocation: { type: Boolean, default: false },
    showMinimap: { type: Boolean, default: true },
    showZoomControls: { type: Boolean, default: true },
    fixedHeight: { type: Number, default: undefined },
    populatedInputs: { type: Boolean, default: false },
});

const { stateStore, stepStore } = useWorkflowStores();
const { scale, activeNodeId, draggingPosition, draggingTerminal } = storeToRefs(stateStore);
const canvas: Ref<HTMLElement | null> = ref(null);

const elementBounding = useElementBounding(canvas, { windowResize: false, windowScroll: false });
const scroll = useScroll(canvas);
const { transform, panBy, setZoom, moveTo } = useD3Zoom(
    scale.value,
    minZoom,
    maxZoom,
    canvas,
    scroll,
    props.initialPosition
);

watch(
    () => transform.value,
    () => {
        stateStore.position[0] = transform.value.x;
        stateStore.position[1] = transform.value.y;
    }
);

const { viewportBoundingBox, updateViewportBaseBoundingBox } = useViewportBoundingBox(
    elementBounding,
    scale,
    transform
);
const { getWorkflowBoundingBox } = useWorkflowBoundingBox();

function fitWorkflow(minimumFitZoom = 0.5, maximumFitZoom = 1.0, padding = 50.0) {
    if (!Object.keys(props.steps).length) {
        // If there are no steps, we cannot fit the workflow.
        return;
    }
    const aabb = getWorkflowBoundingBox();
    aabb.expand(padding);

    const transform = updateViewportBaseBoundingBox().transformTo(aabb);

    const scale = Math.min(transform.scaleX, transform.scaleY);
    const clampedScale = Math.max(minimumFitZoom, Math.min(maximumFitZoom, scale));

    zoomTo(clampedScale);
    moveTo({ x: aabb.x, y: aabb.y }, [0, 0]);
}

const isDragging = ref(false);
provide("isDragging", isDragging);
provide("transform", transform);

watch(
    () => props.scrollToId,
    () => {
        if (props.scrollToId !== null) {
            const scrollToPosition = stateStore.stepPosition[props.scrollToId];
            const step = stepStore.getStep(props.scrollToId);

            assertDefined(scrollToPosition);
            assertDefined(step);

            const { width: stepWidth, height: stepHeight } = scrollToPosition;
            const { position: stepPosition } = step;
            if (stepPosition) {
                const { width, height } = reactive(elementBounding);
                const centerScreenX = width / 2;
                const centerScreenY = height / 2;
                const offsetX = centerScreenX - (stepPosition.left + stepWidth / 2);
                const offsetY = centerScreenY - (stepPosition.top + stepHeight / 2);
                zoomTo(1, { x: offsetX, y: offsetY });
            } else {
                console.log("Step has no position");
            }
            emit("scrollTo");
        }
    }
);

function zoomTo(zoomLevel: number, panTo: XYPosition | null = null, origin?: Vector) {
    setZoom(zoomLevel, origin);
    if (panTo) {
        panBy({ x: panTo.x - transform.value.x, y: panTo.y - transform.value.y });
    }
    stateStore.scale = zoomLevel;
}
function onStopDragging() {
    stateStore.draggingPosition = null;
    stateStore.draggingTerminal = null;
    isDragging.value = false;
}
function onDragConnector(position: TerminalPosition, draggingTerminal: OutputTerminals) {
    stateStore.draggingPosition = position;
    stateStore.draggingTerminal = draggingTerminal;
    isDragging.value = true;
}
function onActivate(nodeId: number | null) {
    emit("stepClicked", nodeId);
    if (activeNodeId.value !== nodeId) {
        stateStore.activeNodeId = nodeId;
    }
}
function onDeactivate() {
    stateStore.activeNodeId = null;
}

watch(
    () => transform.value.k,
    () => (stateStore.scale = transform.value.k)
);

watch(transform, () => emit("transform", transform.value));
watchEffect(() => {
    emit("graph-offset", reactive(elementBounding));
});

const canvasStyle = computed(() => {
    return { transform: `translate(${transform.value.x}px, ${transform.value.y}px) scale(${transform.value.k})` };
});

const { commentStore } = useWorkflowStores();
const { comments } = storeToRefs(commentStore);

const areaHighlight = ref<InstanceType<typeof AreaHighlight>>();

function moveToAndHighlightRegion(bounds: Rectangle) {
    const centerPosition = { x: bounds.x + bounds.width / 2.0, y: bounds.y + bounds.height / 2.0 };
    areaHighlight.value?.show(bounds);
    moveTo(centerPosition);
}

defineExpose({
    fitWorkflow,
    setZoom,
    moveTo,
    moveToAndHighlightRegion,
});
</script>

<template>
    <div id="workflow-canvas" class="unified-panel-body workflow-canvas">
        <ZoomControl
            v-if="props.showZoomControls"
            :zoom-level="scale"
            :pan="transform"
            @onZoom="zoomTo"
            @update:pan="panBy" />
        <ToolBar v-if="!readonly" />
        <div
            id="canvas-container"
            ref="canvas"
            class="canvas-content"
            :style="{ height: props.fixedHeight ? `${props.fixedHeight}vh` : '100%' }"
            @drop.prevent
            @dragover.prevent>
            <AdaptiveGrid
                :viewport-bounds="elementBounding"
                :viewport-bounding-box="viewportBoundingBox"
                :transform="transform" />
            <div class="node-area" :style="canvasStyle">
                <InputCatcher :transform="transform" />
                <BoxSelectPreview />
                <WorkflowEdges
                    :transform="transform"
                    :dragging-terminal="draggingTerminal"
                    :dragging-connection="draggingPosition" />
                <WorkflowNode
                    v-for="(step, key) in steps"
                    :id="step.id"
                    :key="key"
                    :name="step.name"
                    :content-id="step.content_id"
                    :step="step"
                    :datatypes-mapper="datatypesMapper"
                    :active-node-id="activeNodeId"
                    :root-offset="elementBounding"
                    :scroll="scroll"
                    :scale="scale"
                    :readonly="readonly"
                    :is-invocation="props.isInvocation"
                    :populated-inputs="props.populatedInputs"
                    @pan-by="panBy"
                    @stopDragging="onStopDragging"
                    @onDragConnector="onDragConnector"
                    @onActivate="onActivate"
                    @onDeactivate="onDeactivate"
                    v-on="$listeners" />
                <WorkflowComment
                    v-for="comment in comments"
                    :id="`workflow-comment-${comment.id}`"
                    :key="`workflow-comment-${comment.id}`"
                    :comment="comment"
                    :scale="scale"
                    :readonly="readonly"
                    :root-offset="elementBounding"
                    @pan-by="panBy" />
                <AreaHighlight ref="areaHighlight" />
            </div>
        </div>
        <WorkflowMinimap
            v-if="elementBounding && props.showMinimap"
            :steps="steps"
            :comments="comments"
            :viewport-bounds="elementBounding"
            :viewport-bounding-box="viewportBoundingBox"
            @panBy="panBy"
            @moveTo="moveTo" />
        <slot></slot>
    </div>
</template>

<style scoped land="scss">
.workflow-canvas {
    position: relative;

    .canvas-content {
        width: 100%;
        position: relative;
        left: 0px;
        top: 0px;
        overflow: hidden;
    }

    .node-area {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        transform-origin: 0 0;
    }
}
</style>
