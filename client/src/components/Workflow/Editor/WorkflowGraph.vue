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
                    <WorkflowEdges :steps="steps" :dragging-connection="draggingConnection" />
                    <WorkflowNode
                        v-for="(step, key) in steps"
                        :id="step.id"
                        :key="key"
                        :name="step.name"
                        :type="step.type"
                        :content-id="step.content_id"
                        :step="step"
                        :datatypes-mapper="datatypesMapper"
                        :get-manager="getManager"
                        :active-node-id="activeNodeId"
                        :root-offset="position"
                        :scale="scale"
                        @pan-by="onPan"
                        @stopDragging="onStopDragging"
                        @onDragConnector="onDragConnector"
                        @onActivate="onActivate"
                        @onDeactivate="onDeactivate"
                        @onRemove="onRemove"
                        v-on="$listeners" />
                </div>
            </d3-zoom>
        </div>
        <Minimap
            :nodes="nodes"
            :steps="steps"
            :root-offset="position"
            :scale="scale"
            :pan="transform"
            @pan-by="onPan"
            @moveTo="onMoveTo" />
    </div>
</template>
<script setup>
import ZoomControl from "./ZoomControl";
import WorkflowNode from "./Node";
import WorkflowEdges from "./WorkflowEdges.vue";
import Minimap from "./Minimap.vue";
import { computed, reactive, ref } from "vue";
import { useElementBounding } from "@vueuse/core";
import D3Zoom from "./D3Zoom.vue";
import { provide } from "vue";
import { useScale, setScale, useActiveNodeId, setActiveNodeId } from "./composables/useWorkflowState";

defineProps({
    steps: {
        type: Object,
        required: true,
    },
    getManager: {
        type: Function,
        default: null,
    },
    datatypesMapper: {
        type: Object,
        default: null,
    },
    nodes: {
        type: Object,
        required: true,
    },
});
const transform = reactive({ x: 0, y: 0, k: 1 });

const draggingConnection = ref(null);
const isDragging = ref(false);
provide("draggingConnection", draggingConnection);
provide("isDragging", isDragging);
provide("transform", transform);
const scale = useScale();
const activeNodeId = useActiveNodeId();
const el = ref(null);
const zoom = ref(null);
const position = reactive(useElementBounding(el, { windowResize: false, windowScroll: false }));

function onPan(pan) {
    zoom.value.panBy(pan);
}
function onZoom(zoomLevel, panTo = null) {
    zoom.value.setZoom(zoomLevel);
    if (panTo) {
        onPan({ x: panTo.x - this.transform.x, y: panTo.y - this.transform.y });
    }
    setScale(zoomLevel);
}
function onMoveTo(moveTo) {
    zoom.value.moveTo(moveTo);
}
function onResetAll() {
    onZoom(1, { x: 0, y: 0 });
}
function onStopDragging() {
    draggingConnection.value = null;
    isDragging.value = false;
}
function onDragConnector(vector) {
    isDragging.value = true;
    draggingConnection.value = vector;
}
function onActivate(nodeId) {
    if (activeNodeId != nodeId) {
        setActiveNodeId(nodeId);
    }
}
function onDeactivate() {
    setActiveNodeId(null);
}
function onRemove(nodeId) {
    emit("onRemove", nodeId);
}

function onTransform(newTransform) {
    transform.x = newTransform.x;
    transform.y = newTransform.y;
    transform.k = newTransform.k;
    setScale(transform.k);
}

const nodesStyle = computed(() => {
    return { transform: `translate(${transform.x}px, ${transform.y}px) scale(${transform.k})` };
});

const emit = defineEmits(["transform", "graph-offset", "onRemove"]);
emit("transform", transform);
emit("graph-offset", position);
</script>
