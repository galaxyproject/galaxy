<template>
    <div id="workflow-canvas" class="unified-panel-body workflow-canvas">
        <ZoomControl
            :zoom-level="scale"
            :pan="transform"
            @onZoom="onZoom"
            @reset-all="onResetAll"
            @update:pan="onPan" />
        <div ref="el" class="canvas-viewport" @drop.prevent @dragover.prevent>
            <d3-zoom id="canvas-container" ref="zoom" @transform="onTransform">
                <div ref="nodes" class="node-area" :style="nodesStyle">
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
                        @pan-by="onPan"
                        @stopDragging="onStopDragging"
                        @onDragConnector="onDragConnector"
                        @onActivate="onActivate"
                        @onDeactivate="onDeactivate"
                        v-on="$listeners" />
                </div>
            </d3-zoom>
        </div>
        <Minimap
            v-if="position"
            :steps="steps"
            :root-offset="position"
            :scale="scale"
            :pan="transform"
            @pan-by="onPan"
            @moveTo="onMoveTo" />
    </div>
</template>
<script lang="ts" setup>
import ZoomControl from "@/components/Workflow/Editor/ZoomControl.vue";
import WorkflowNode from "@/components/Workflow/Editor/Node.vue";
import WorkflowEdges from "@/components/Workflow/Editor/WorkflowEdges.vue";
import Minimap from "@/components/Workflow/Editor/Minimap.vue";
import { computed, reactive, ref } from "vue";
import { useElementBounding } from "@vueuse/core";
import D3Zoom from "@/components/Workflow/Editor/D3Zoom.vue";
import { provide } from "vue";
import { storeToRefs } from "pinia";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import type { PropType } from "vue";
import type { TerminalPosition } from "@/stores/workflowEditorStateStore";
import { DatatypesMapperModel } from "@/components/Datatypes/model";
import type { Step } from "@/stores/workflowStepStore";
import type { XYPosition } from "@/stores/workflowEditorStateStore";
import type { ZoomTransform } from "d3-zoom";
import type { OutputTerminals } from "./modules/terminals";

defineProps({
    steps: { type: Object as PropType<{ [index: string]: Step }>, required: true },
    datatypesMapper: { type: DatatypesMapperModel, required: true },
    highlightId: { type: null as unknown as PropType<number | null> },
});
const transform = reactive({ x: 0, y: 0, k: 1 });

const isDragging = ref(false);
provide("isDragging", isDragging);
provide("transform", transform);

const stateStore = useWorkflowStateStore();
const { scale, activeNodeId, draggingPosition, draggingTerminal } = storeToRefs(stateStore);
const el = ref(null);
const zoom = ref(null) as any;
const position = reactive(useElementBounding(el, { windowResize: false, windowScroll: false }));

function onPan(pan: XYPosition) {
    zoom.value.panBy(pan);
}
function onZoom(zoomLevel: number, panTo: XYPosition | null = null) {
    zoom.value.setZoom(zoomLevel);
    if (panTo) {
        onPan({ x: panTo.x - transform.x, y: panTo.y - transform.y });
    }
    stateStore.setScale(zoomLevel);
}
function onMoveTo(moveTo: XYPosition) {
    zoom.value.moveTo(moveTo);
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

function onTransform(newTransform: ZoomTransform) {
    transform.x = newTransform.x;
    transform.y = newTransform.y;
    transform.k = newTransform.k;
    stateStore.setScale(transform.k);
}

const nodesStyle = computed(() => {
    return { transform: `translate(${transform.x}px, ${transform.y}px) scale(${transform.k})` };
});

const emit = defineEmits(["transform", "graph-offset", "onRemove"]);
emit("transform", transform);
emit("graph-offset", position);
</script>
