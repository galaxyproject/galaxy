<template>
    <div id="workflow-canvas" class="unified-panel-body workflow-canvas">
        <ZoomControl :zoom-level="scale" :pan="transform" @onZoom="onZoom" @update:pan="panBy" />
        <div id="canvas-container" ref="canvas" class="canvas-content" @drop.prevent @dragover.prevent>
            <!-- canvas-background is sibling of node-area because it has a different transform origin, so can't be parent of node-area -->
            <div class="canvas-background" :style="canvasStyle" />
            <div class="node-area" :style="canvasStyle">
                <WorkflowEdges :dragging-terminal="draggingTerminal" :dragging-connection="draggingPosition" />
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
                    @pan-by="panBy"
                    @stopDragging="onStopDragging"
                    @onDragConnector="onDragConnector"
                    @onActivate="onActivate"
                    @onDeactivate="onDeactivate"
                    v-on="$listeners" />
            </div>
        </div>
        <workflow-minimap
            v-if="elementBounding"
            :steps="steps"
            :viewport-bounds="elementBounding"
            :viewport-scale="scale"
            :viewport-pan="transform"
            @panBy="panBy"
            @moveTo="moveTo" />
    </div>
</template>
<script lang="ts" setup>
import ZoomControl from "@/components/Workflow/Editor/ZoomControl.vue";
import WorkflowNode from "@/components/Workflow/Editor/Node.vue";
import WorkflowEdges from "@/components/Workflow/Editor/WorkflowEdges.vue";
import WorkflowMinimap from "@/components/Workflow/Editor/WorkflowMinimap.vue";
import { computed, provide, reactive, ref, watch, type Ref, type PropType, watchEffect } from "vue";
import { useElementBounding, useScroll } from "@vueuse/core";
import { storeToRefs } from "pinia";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import type { TerminalPosition } from "@/stores/workflowEditorStateStore";
import { DatatypesMapperModel } from "@/components/Datatypes/model";
import { useWorkflowStepStore, type Step } from "@/stores/workflowStepStore";
import { useD3Zoom } from "./composables/d3Zoom";
import type { XYPosition } from "@/stores/workflowEditorStateStore";
import type { OutputTerminals } from "./modules/terminals";
import { assertDefined } from "@/utils/assertions";
import { minZoom, maxZoom } from "./modules/zoomLevels";

const emit = defineEmits(["transform", "graph-offset", "onRemove", "scrollTo"]);
const props = defineProps({
    steps: { type: Object as PropType<{ [index: string]: Step }>, required: true },
    datatypesMapper: { type: DatatypesMapperModel, required: true },
    highlightId: { type: null as unknown as PropType<number | null>, default: null },
    scrollToId: { type: null as unknown as PropType<number | null>, default: null },
});

const stateStore = useWorkflowStateStore();
const stepStore = useWorkflowStepStore();
const { scale, activeNodeId, draggingPosition, draggingTerminal } = storeToRefs(stateStore);
const canvas: Ref<HTMLElement | null> = ref(null);

const elementBounding = useElementBounding(canvas, { windowResize: false, windowScroll: false });
const scroll = useScroll(canvas);
const { transform, panBy, setZoom, moveTo } = useD3Zoom(1, minZoom, maxZoom, canvas, scroll, { x: 20, y: 20 });

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
