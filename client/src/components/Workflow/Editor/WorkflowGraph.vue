<template>
    <div id="workflow-canvas" class="unified-panel-body workflow-canvas">
        <ZoomControl
            :zoom-level="zoomLevel"
            :pan="transform"
            @onZoom="onZoomButton"
            @reset-all="onResetAll"
            @update:pan="onPan" />
        <div ref="el" class="canvas-viewport" @drop.prevent>
            <d3-zoom ref="d3Zoom" id="canvas-container" @transform="onTransform" @dragging="onDrag" @scaling="onScale">
                <div ref="nodes" class="node-area" :style="nodesStyle">
                    <svg class="canvas-svg node-area">
                        <raw-connector v-if="draggingConnection" :position="draggingConnection"></raw-connector>
                        <terminal-connector
                            v-for="connection in connections"
                            :key="connection.id"
                            :connection="connection"></terminal-connector>
                    </svg>
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
import RawConnector from "./Connector";
import TerminalConnector from "./TerminalConnector";
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
        RawConnector,
        TerminalConnector,
        WorkflowNode,
        Minimap,
        ZoomControl,
    },
    data() {
        return {
            isWheeled: false,
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
        onMoveTo(moveTo) {
            // implement me
        },
        onResetAll() {
            this.pan = { x: 0, y: 0 };
            this.setScale(1);
        },
        onDrag(panData) {
            console.log("panData", panData);
            this.pan = { x: panData.x, y: panData.y };
        },
        onScale(scaleData) {
            console.log("scaleData", scaleData);
            this.pan = {
                x: scaleData.translateX * scaleData.scale,
                y: scaleData.translateY * scaleData.scale,
            };
            console.log(this.pan);
            this.setScale(scaleData.scale);
        },
        onUpdatedCTM(CTM) {
            this.transform = CTM;
        },
        onZoom(zoomLevel) {
            // SvgZoomPanel returns array
            this.setScale(zoomLevel?.[0]);
        },
        onStopDragging() {
            this.draggingConnection = null;
        },
        onDragConnector(vector) {
            this.draggingConnection = vector;
        },
        onZoomButton(zoomLevel) {
            this.$refs.d3Zoom.setZoom(zoomLevel);
            this.setScale(zoomLevel);
        },
        onActivate(nodeId) {
            if (this.activeNodeId != nodeId) {
                this.$store.commit("workflowState/setActiveNode", nodeId);
                // this.canvasManager.drawOverview();
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
            return this.$store.getters["workflowState/getActiveNode"]();
        },
        connections() {
            const connections = [];
            Object.entries(this.steps).forEach(([stepId, step]) => {
                if (step.input_connections) {
                    Object.entries(step?.input_connections).forEach(([input_name, outputArray]) => {
                        if (!Array.isArray(outputArray)) {
                            outputArray = [outputArray];
                        }
                        outputArray.forEach((output) => {
                            const connection = {
                                id: `${step.id}-${input_name}-${output.id}-${output.output_name}`,
                                inputStepId: step.id,
                                inputName: input_name,
                                outputStepId: output.id,
                                outputName: output.output_name,
                            };
                            connections.push(connection);
                        });
                    });
                }
            });
            return connections;
        },
    },
};
</script>
