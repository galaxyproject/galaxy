<template>
    <div id="workflow-canvas" class="unified-panel-body workflow-canvas">
        <ZoomControl v-if="!checkWheeled" :zoom-level="zoomLevel" @onZoom="onZoom" />
        <b-button
            v-else
            v-b-tooltip.hover
            class="reset-wheel"
            variant="light"
            title="Show Zoom Buttons"
            size="sm"
            aria-label="Show Zoom Buttons"
            @click="resetWheel">
            Zoom Controls
        </b-button>
        <div id="canvas-viewport">
            <div id="canvas-container" ref="canvas">
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
                    :get-canvas-manager="getCanvasManager"
                    :activeNodeId="activeNodeId"
                    @onActivate="onActivate"
                    @onRemove="onRemove"
                    v-on="$listeners" />
                <workflow-connection
                    v-for="(step, key) in steps"
                    :key="`${key}-c`"
                    :step="step"
                    :canvas-manager="canvasManager"
                    :get-manager="getManager" />
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

export default {
    components: {
        WorkflowNode,
        ZoomControl,
        WorkflowConnection,
    },
    data() {
        return {
            isWheeled: false,
            canvasManager: null,
            zoomLevel: 7,
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
        this.canvasManager = new WorkflowCanvas(this.getManager(), this.$refs.canvas);
        this.canvasManager.drawOverview();
        this.canvasManager.scrollToNodes();
    },
    methods: {
        getCanvasManager() {
            return this.canvasManager;
        },
        onZoom(zoomLevel) {
            this.zoomLevel = this.canvasManager.setZoom(zoomLevel);
        },
        resetWheel() {
            this.zoomLevel = this.canvasManager.zoomLevel;
            this.canvasManager.isWheeled = false;
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
        checkWheeled() {
            if (this.canvasManager != null) {
                return this.canvasManager.isWheeled;
            }
            return this.isWheeled;
        },
    },
};
</script>
