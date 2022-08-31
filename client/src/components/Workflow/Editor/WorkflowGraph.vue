<template>
    <div id="workflow-canvas" class="unified-panel-body workflow-canvas">
        <ZoomControl :zoom-level="zoomLevel" @onZoom="onZoom" />
        <div
            class="canvas-viewport"
            @dragover.prevent
            @drop.prevent
            @mousemove="handleMove"
            @mouseup="handleUp"
            @mousedown="handleDown">
            <div id="canvas-container" ref="canvas">
                <svg width="100%" height="100%">
                    <connector :startX="0" :endX="100" :startY="0" :endY="100"></connector>
                    <connector
                        v-if="draggingConnection"
                        :startX="draggingConnection.startX"
                        :endX="draggingConnection.endX"
                        :startY="draggingConnection.startY"
                        :endY="draggingConnection.endY"></connector>
                    <!--
                        <workflow-connection
                            v-for="(step, key) in steps"
                            :key="`${key}-c`"
                            :step="step">
                            -->
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
                    @stop="onStop"
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
import WorkflowCanvas from "./modules/canvas";
import ZoomControl from "./ZoomControl";
import WorkflowNode from "./Node";
import WorkflowConnection from "./WorkflowConnection";
import Connector from "./Connector.vue";

export default {
    components: {
        Connector,
        WorkflowNode,
        ZoomControl,
        WorkflowConnection,
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
        onStop() {
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
                this.$store.commit("setActiveNode", nodeId);
                this.canvasManager.drawOverview();
            }
        },
        onDeactivate() {
            this.$store.commit("setActiveNode", null);
        },
        onRemove(nodeId) {
            this.$emit("onRemove", nodeId);
        },
    },
    computed: {
        activeNodeId() {
            return this.$store.getters.getActiveNode();
        },
    },
};
</script>
