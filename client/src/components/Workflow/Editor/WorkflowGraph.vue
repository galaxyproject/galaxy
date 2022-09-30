<template>
    <div id="workflow-canvas" class="unified-panel-body workflow-canvas">
        <ZoomControl
            :zoom-level="zoomLevel"
            :pan="transform"
            @onZoom="onZoom"
            @reset-all="onResetAll"
            @update:pan="onPan" />
        <div ref="el" class="canvas-viewport" @drop.prevent>
            <d3-zoom ref="d3Zoom" id="canvas-container" @transform="onTransform">
                <div ref="nodes" class="node-area" :style="nodesStyle">
                    <WorkflowEdges :steps="steps" :dragging-connection="draggingConnection" />
                    <WorkflowNode
                        v-for="(step, key) in steps"
                        :id="key"
                        :key="key"
                        :name="step.name"
                        :type="step.type"
                        :content-id="step.content_id"
                        :step="step"
                        :datatypes-mapper="datatypesMapper"
                        :get-manager="getManager"
                        :activeNodeId="activeNodeId"
                        :root-offset="position"
                        :scale="zoomLevel"
                        @pan-by="onPan"
                        @stopDragging="onStopDragging"
                        @onDragConnector="onDragConnector"
                        @onActivate="onActivate"
                        @onRemove="onRemove"
                        v-on="$listeners" />
                </div>
            </d3-zoom>
        </div>
        <Minimap
            :nodes="nodes"
            :steps="steps"
            :root-offset="position"
            :scale="zoomLevel"
            :pan="transform"
            @pan-by="onPan"
            @moveTo="onMoveTo" />
    </div>
</template>
<script>
import ZoomControl from "./ZoomControl";
import WorkflowNode from "./Node";
import WorkflowEdges from "./WorkflowEdges.vue";
import Minimap from "./Minimap.vue";
import { reactive, ref } from "vue";
import { useElementBounding } from "@vueuse/core";
import D3Zoom from "./D3Zoom.vue";
import { provide } from "vue";
import { useScale, setScale } from "./composables/useScale";

export default {
    setup() {
        const transform = reactive({ x: 0, y: 0, k: 1 });

        function onTransform(newTransform) {
            transform.x = newTransform.x;
            transform.y = newTransform.y;
            transform.k = newTransform.k;
            setScale(transform.k);
        }
        provide("transform", transform);
        const scale = useScale();
        const el = ref(null);
        const position = reactive(useElementBounding(el, { windowResize: false, windowScroll: false }));
        return { el, position, zoomLevel: scale, onTransform, transform, setScale };
    },
    components: {
        D3Zoom,
        WorkflowEdges,
        WorkflowNode,
        Minimap,
        ZoomControl,
    },
    data() {
        return {
            draggingConnection: null,
        };
    },
    props: {
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
    },
    methods: {
        onPan(pan) {
            this.$refs.d3Zoom.panBy(pan);
        },
        onZoom(zoomLevel, panTo = null) {
            this.$refs.d3Zoom.setZoom(zoomLevel);
            if (panTo) {
                this.onPan({ x: panTo.x - this.transform.x, y: panTo.y - this.transform.y });
            }
            this.setScale(zoomLevel);
        },
        onMoveTo(moveTo) {
            this.$refs.d3Zoom.moveTo(moveTo);
        },
        onResetAll() {
            this.onZoom(1, { x: 0, y: 0 });
        },
        onScale(scaleData) {
            this.pan = {
                x: scaleData.translateX * scaleData.scale,
                y: scaleData.translateY * scaleData.scale,
            };
            this.setScale(scaleData.scale);
        },
        onStopDragging() {
            this.draggingConnection = null;
        },
        onDragConnector(vector) {
            this.draggingConnection = vector;
        },
        onActivate(nodeId) {
            if (this.activeNodeId != nodeId) {
                this.$store.commit("workflowState/setActiveNode", nodeId);
            }
        },
        onDeactivate() {
            this.$store.commit("workflowState/setActiveNode", null);
        },
        onRemove(nodeId) {
            this.$emit("onRemove", nodeId);
        },
    },
    computed: {
        nodesStyle() {
            const transform = `translate(${this.transform.x}px, ${this.transform.y}px) scale(${this.transform.k})`;
            return { transform };
        },
        activeNodeId() {
            return this.$store.getters["workflowState/getActiveNode"];
        },
    },
};
</script>
