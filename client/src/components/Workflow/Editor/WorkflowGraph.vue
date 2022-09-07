<template>
    <div id="workflow-canvas" class="unified-panel-body workflow-canvas">
        <ZoomControl :zoom-level="zoomLevel" @onZoom="onZoomButton" />
        <div class="canvas-viewport" @dragover.prevent @drop.prevent>
            <panZoom
                style="width: 100%; height: 100%"
                selector=".zoomable"
                :options="panZoomOptions"
                @init="onInitPanZoom"
                @transform="onTransform">
                <div id="canvas-container" ref="canvas">
                    <!--
                    <Draggable style="width: 100%; height: 100%" @move="onPanContainer" :apply-scale="false">
                        -->
                    <svg class="canvas-svg" width="100%" height="100%" ref="svg">
                        <g class="zoomable">
                            <raw-connector v-if="draggingConnection" :position="draggingConnection"></raw-connector>
                            <terminal-connector
                                v-for="connection in connections"
                                :key="connection.id"
                                :connection="connection"></terminal-connector>
                        </g>
                    </svg>
                    <div class="nodeArea" ref="nodes" :style="style">
                        <!-- this div is only necessary so that we synchronize zoom and pan to the svg coordinates -->
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
                            :root-offset="rootOffset"
                            @pan-by="onPan"
                            @stopDragging="onStopDragging"
                            @onDragConnector="onDragConnector"
                            @onActivate="onActivate"
                            @onRemove="onRemove"
                            v-on="$listeners" />
                    </div>
                    <!--
                    </Draggable>
                    -->
                </div>
            </panZoom>
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
import TerminalConnector from "./TerminalConnector";
import Draggable from "./Draggable.vue";
import panZoom from "vue-panzoom";
import Vue from "vue";
// install plugin
Vue.use(panZoom);

export default {
    components: {
        Draggable,
        RawConnector,
        TerminalConnector,
        WorkflowNode,
        ZoomControl,
    },
    data() {
        return {
            isWheeled: false,
            rootOffset: { left: 0, top: 0 },
            draggingConnection: null,
            panzoom: null,
            panZoomOptions: {
                transformOrigin: null,
                minZoom: 0.1,
                maxZoom: 10,
            },
            transform: null,
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
        setScale(scale) {
            this.$store.commit("workflowState/setScale", scale);
        },
        onTransform(e) {
            this.transform = e.getTransform();
            this.setScale(this.transform.scale);
        },
        onStopDragging() {
            this.draggingConnection = null;
        },
        onDragConnector(vector) {
            this.draggingConnection = vector;
        },
        onZoomButton(zoomLevel) {
            this.panzoom.zoomAbs(
                this.rootOffset.left + this.rootOffset.width / 2,
                this.rootOffset.top + this.rootOffset.height / 2,
                zoomLevel
            );
        },
        onInitPanZoom(panzoomInstance) {
            this.panzoom = panzoomInstance;
        },
        onPan(pan) {
            this.panzoom.moveBy(pan.x, pan.y);
        },
        onPanContainer(e) {
            this.panzoom.moveBy(e.data.deltaX, e.data.deltaY);
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
        style() {
            if (this.transform) {
                return `transform: matrix(${this.transform.scale}, 0, 0, ${this.transform.scale}, ${this.transform.x}, ${this.transform.y})`;
            }
        },
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
