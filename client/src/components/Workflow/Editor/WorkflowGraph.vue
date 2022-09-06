<template>
    <div id="workflow-canvas" class="unified-panel-body workflow-canvas">
        <ZoomControl :zoom-level="zoomLevel" @onZoom="onZoomButton" />
        <div class="canvas-viewport" @dragover.prevent @drop.prevent>
            <div id="canvas-container" ref="canvas">
                <SvgPanZoom
                    style="width: 100%; height: 100%"
                    :minZoom="0.1"
                    :zoomEnabled="true"
                    :controlIconsEnabled="false"
                    :fit="false"
                    :center="false"
                    :on-zoom="onZoom"
                    @svgpanzoom="registerSvgPanZoom">
                    <svg class="canvas-svg" width="100%" height="100%" ref="svg">
                        <g>
                            <raw-connector v-if="draggingConnection" :position="draggingConnection"></raw-connector>
                            <terminal-connector
                                v-for="connection in connections"
                                :key="connection.id"
                                :connection="connection"></terminal-connector>
                            <foreignObject style="overflow: visible">
                                <WorkflowNode
                                    xmlns="http://www.w3.org/1999/xhtml"
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
                                    :root-offset="rootOffset"
                                    @pan-by="onPan"
                                    @stopDragging="onStopDragging"
                                    @onDragConnector="onDragConnector"
                                    @onActivate="onActivate"
                                    @onRemove="onRemove"
                                    v-on="$listeners" />
                            </foreignObject>
                        </g>
                    </svg>
                </SvgPanZoom>
            </div>
        </div>
        <div class="workflow-overview" aria-hidden="true">
            <div class="workflow-overview-body">
                <div id="overview-container">
                    <canvas id="overview-canvas" width="0" height="0" />
                    <div id="overview-viewport" />
                </div>
            </div>
        </div>
    </div>
</template>
<script>
import ZoomControl from "./ZoomControl";
import WorkflowNode from "./Node";
import RawConnector from "./Connector";
import SvgPanZoom from "vue-svg-pan-zoom";
import TerminalConnector from "./TerminalConnector";

export default {
    components: {
        RawConnector,
        SvgPanZoom,
        TerminalConnector,
        WorkflowNode,
        ZoomControl,
    },
    data() {
        return {
            isWheeled: false,
            rootOffset: { left: 0, top: 0 },
            draggingConnection: null,
            svgpanzoom: null,
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
    },
    mounted() {
        // canvas overview management
        const rootRect = this.$refs.canvas.getBoundingClientRect();
        this.rootOffset = {
            top: rootRect.top,
            left: rootRect.left,
            width: rootRect.width,
            height: rootRect.height,
            bottom: rootRect.bottom,
            right: rootRect.right,
        };
        console.log(`root offset: ${this.rootOffset}`);

        // this.canvasManager = new WorkflowCanvas(this.getManager(), this.$refs.canvas);
        // this.canvasManager.drawOverview();
        // this.canvasManager.scrollToNodes();
    },
    methods: {
        onStopDragging() {
            this.draggingConnection = null;
        },
        onDragConnector(vector) {
            this.draggingConnection = vector;
        },
        onZoom(zoomLevel) {
            // SvgZoomPanel returns array
            this.$store.commit("workflowState/setScale", zoomLevel?.[0]);
        },
        onZoomButton(zoomLevel) {
            this.$store.commit("workflowState/setScale", zoomLevel);
            this.svgpanzoom.zoom(zoomLevel);
        },
        registerSvgPanZoom(svgpanzoom) {
            this.svgpanzoom = svgpanzoom;
        },
        onPan(pan) {
            this.svgpanzoom.panBy(pan);
        },
        onActivate(nodeId) {
            console.log("onNodeId", nodeId);
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
        zoomLevel() {
            return this.$store.getters["workflowState/getScale"]();
        },
        activeNodeId() {
            return this.$store.getters["workflowState/getActiveNode"]();
        },
        connections() {
            console.log("connection fired");
            const connections = [];
            Object.entries(this.steps).forEach(([stepId, step]) => {
                Object.entries(step.input_connections).forEach(([input_name, outputArray]) => {
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
            });
            return connections;
        },
    },
};
</script>
