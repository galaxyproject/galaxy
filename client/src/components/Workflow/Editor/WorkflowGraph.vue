<template>
    <div id="workflow-canvas" class="unified-panel-body workflow-canvas">
        <ZoomControl :zoom-level="zoomLevel" @onZoom="onZoom" />
        <div
            class="canvas-viewport"
            @dragover.prevent
            @drop.prevent
            @mousemove="handleMove"
            @mouseup="handleUp"
            @mousedown.prevent.stop="handleDown">
            <div id="canvas-container" ref="canvas">
                <svg class="canvas-svg">
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
                    :root-offset="rootOffset"
                    @stopDragging="onStopDragging"
                    @onDragConnector="onDragConnector"
                    @onActivate="onActivate"
                    @onRemove="onRemove"
                    v-on="$listeners" />
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
import TerminalConnector from "./TerminalConnector";

export default {
    components: {
        RawConnector,
        TerminalConnector,
        WorkflowNode,
        ZoomControl,
    },
    data() {
        return {
            zoomLevel: 1,
            isWheeled: false,
            rootOffset: { left: 0, top: 0 },
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
    },
    mounted() {
        // canvas overview management
        const rootRect = this.$refs.canvas.getBoundingClientRect();
        this.rootOffset = { top: rootRect.top, left: rootRect.left };
        console.log(`root offset: ${this.rootOffset}`);

        // this.canvasManager = new WorkflowCanvas(this.getManager(), this.$refs.canvas);
        // this.canvasManager.drawOverview();
        // this.canvasManager.scrollToNodes();
    },
    methods: {
        onStopDragging() {
            console.log("onStop");
            this.draggingConnection = null;
        },
        onDragConnector(vector) {
            this.draggingConnection = vector;
        },
        handleMove(e) {
            // console.log(e);
        },
        handleUp(e) {
            console.log(e);
        },
        handleDown(e) {
            console.log(e);
        },
        onZoom(zoomLevel) {
            this.zoomLevel = zoomLevel;
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
