<template>
    <div id="workflow-canvas" class="unified-panel-body workflow-canvas">
        <ZoomControl
            :zoom-level="scale"
            :pan="transform"
            @onZoom="onZoom"
            @reset-all="onResetAll"
            @update:pan="panBy" />
        <div ref="canvas" class="canvas-content" @drop.prevent @dragover.prevent>
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
                    :root-offset="position"
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
            v-if="position"
            :steps="steps"
            :root-offset="position"
            :scale="scale"
            :pan="transform"
            @pan-by="panBy"
            @moveTo="moveTo" />
    </div>
</template>
<script lang="ts" setup>
import ZoomControl from "@/components/Workflow/Editor/ZoomControl.vue";
import WorkflowNode from "@/components/Workflow/Editor/Node.vue";
import WorkflowEdges from "@/components/Workflow/Editor/WorkflowEdges.vue";
import WorkflowMinimap from "@/components/Workflow/Editor/WorkflowMinimap.vue";
import { computed, provide, reactive, ref, watch, type Ref, type PropType } from "vue";
import { useElementBounding } from "@vueuse/core";
import { storeToRefs } from "pinia";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import type { TerminalPosition } from "@/stores/workflowEditorStateStore";
import { DatatypesMapperModel } from "@/components/Datatypes/model";
import { useWorkflowStepStore, type Step } from "@/stores/workflowStepStore";
import { useZoom } from "./composables/useZoom";
import type { XYPosition } from "@/stores/workflowEditorStateStore";
import type { OutputTerminals } from "./modules/terminals";

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
const { transform, panBy, setZoom, moveTo } = useZoom(1, 0.2, 5, canvas);

const position = reactive(useElementBounding(canvas, { windowResize: false, windowScroll: false }));

const isDragging = ref(false);
provide("isDragging", isDragging);
provide("transform", transform);

watch(
    () => props.scrollToId,
    () => {
        if (props.scrollToId !== null) {
            const { width: stepWidth, height: stepHeight } = stateStore.stepPosition[props.scrollToId];
            const { position: stepPosition } = stepStore.getStep(props.scrollToId);
            if (stepPosition) {
                const { width, height } = position;
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
function onResetAll() {
    onZoom(1, { x: 0, y: 0 });
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

const canvasStyle = computed(() => {
    return { transform: `translate(${transform.value.x}px, ${transform.value.y}px) scale(${transform.value.k})` };
});

const emit = defineEmits(["transform", "graph-offset", "onRemove", "scrollTo"]);
emit("transform", transform);
emit("graph-offset", position);
</script>
