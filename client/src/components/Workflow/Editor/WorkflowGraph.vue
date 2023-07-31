<template>
    <div id="workflow-canvas" class="unified-panel-body workflow-canvas">
        <ZoomControl :zoom-level="scale" :pan="transform" @onZoom="onZoom" @update:pan="panBy" />
        <div id="canvas-container" ref="canvas" class="canvas-content" @drop.prevent @dragover.prevent>
            <AdaptiveGrid
                :viewport-bounds="elementBounding"
                :viewport-bounding-box="viewportBoundingBox"
                :transform="transform" />
            <div class="node-area" :style="canvasStyle">
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
                    @pan-by="panBy"
                    @stopDragging="onStopDragging"
                    @onDragConnector="onDragConnector"
                    @onActivate="onActivate"
                    @onDeactivate="onDeactivate"
                    v-on="$listeners" />
            </div>
        </div>
        <WorkflowMinimap
            v-if="elementBounding"
            :steps="steps"
            :viewport-bounds="elementBounding"
            :viewport-bounding-box="viewportBoundingBox"
            @panBy="panBy"
            @moveTo="moveTo" />
    </div>
</template>
<script setup lang="ts">
import { useElementBounding, useScroll } from "@vueuse/core";
import { storeToRefs } from "pinia";
import { computed, type PropType, provide, reactive, type Ref, ref, watch, watchEffect } from "vue";

import { DatatypesMapperModel } from "@/components/Datatypes/model";
import type { TerminalPosition, XYPosition } from "@/stores/workflowEditorStateStore";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { type Step, useWorkflowStepStore } from "@/stores/workflowStepStore";
import { assertDefined } from "@/utils/assertions";

import { useD3Zoom } from "./composables/d3Zoom";
import { useViewportBoundingBox } from "./composables/viewportBoundingBox";
import type { OutputTerminals } from "./modules/terminals";
import { maxZoom, minZoom } from "./modules/zoomLevels";

import AdaptiveGrid from "./AdaptiveGrid.vue";
import WorkflowNode from "@/components/Workflow/Editor/Node.vue";
import WorkflowEdges from "@/components/Workflow/Editor/WorkflowEdges.vue";
import WorkflowMinimap from "@/components/Workflow/Editor/WorkflowMinimap.vue";
import ZoomControl from "@/components/Workflow/Editor/ZoomControl.vue";

const emit = defineEmits(["transform", "graph-offset", "onRemove", "scrollTo"]);
const props = defineProps({
    steps: { type: Object as PropType<{ [index: string]: Step }>, required: true },
    datatypesMapper: { type: DatatypesMapperModel, required: true },
    highlightId: { type: Number as PropType<number | null>, default: null },
    scrollToId: { type: Number as PropType<number | null>, default: null },
    readonly: { type: Boolean, default: false },
});

const stateStore = useWorkflowStateStore();
const stepStore = useWorkflowStepStore();
const { scale, activeNodeId, draggingPosition, draggingTerminal } = storeToRefs(stateStore);
const canvas: Ref<HTMLElement | null> = ref(null);

const elementBounding = useElementBounding(canvas, { windowResize: false, windowScroll: false });
const scroll = useScroll(canvas);
const { transform, panBy, setZoom, moveTo } = useD3Zoom(1, minZoom, maxZoom, canvas, scroll, { x: 20, y: 20 });
const { viewportBoundingBox } = useViewportBoundingBox(elementBounding, scale, transform);

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
                onZoom(1, { x: offsetX, y: offsetY });
            } else {
                console.log("Step has no position");
            }
            emit("scrollTo");
        }
    }
);

function onZoom(zoomLevel: number, panTo: XYPosition | null = null) {
    setZoom(zoomLevel);
    if (panTo) {
        panBy({ x: panTo.x - transform.value.x, y: panTo.y - transform.value.y });
    }
    stateStore.setScale(zoomLevel);
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
    if (activeNodeId.value !== nodeId) {
        stateStore.setActiveNode(nodeId);
    }
}
function onDeactivate() {
    stateStore.setActiveNode(null);
}

watch(
    () => transform.value.k,
    () => stateStore.setScale(transform.value.k)
);

watch(transform, () => emit("transform", transform.value));
watchEffect(() => {
    emit("graph-offset", reactive(elementBounding));
});

const canvasStyle = computed(() => {
    return { transform: `translate(${transform.value.x}px, ${transform.value.y}px) scale(${transform.value.k})` };
});
</script>

<style scoped land="scss">
.workflow-canvas {
    position: relative;

    .canvas-content {
        width: 100%;
        height: 100%;
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
