<template>
    <div id="workflow-canvas" class="unified-panel-body workflow-canvas">
        <ZoomControl
            :zoom-level="zoomLevel"
            :pan="pan"
            @onZoom="onZoomButton"
            @reset-all="onResetAll"
            @update:pan="onPan" />
        <div ref="el" class="canvas-viewport" @drop.prevent>
            <d3-zoom
                id="canvas-container"
                ref="zoomControl"
                :within="false"
                throttleDelay="16"
                wheelVelocity="0.0015"
                @transform="onTransform"
                @dragging="onDrag"
                @scaling="onScale">
                <svg :width="position.width" :height="position.height" class="canvas-svg">
                    <svg>
                        <raw-connector v-if="draggingConnection" :position="draggingConnection"></raw-connector>
                        <terminal-connector
                            v-for="connection in connections"
                            :key="connection.id"
                            :connection="connection"></terminal-connector>
                    </svg>
                </svg>
                <div ref="nodes" class="nodeArea">
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
            :pan="pan"
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

export default {
    setup() {
        const el = ref(null);
        const position = reactive(useElementBounding(el));
        return { el, position };
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
            svgpanzoom: null,
            transform: null,
            pan: { x: 0, y: 0 },
            transform: "",
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
        onTransform(transform) {
            const cssTransform = `translate(${transform.x}px, ${transform.y}px) scale(${transform.k})`;
            this.transform = transform.toString();
            this.$refs.nodes.style.transform = cssTransform;
        },
        onPan(pan) {
            console.log("onPan", pan);
            this.pan = pan;
            this.$refs.zoomControl.setData({
                scale: this.scale,
                originX: pan.x,
                originY: pan.y,
                translateX: pan.x,
                translateY: pan.y,
            });
        },
        onResetAll() {
            this.pan = { x: 0, y: 0 };
            this.setScale(1);
            this.$refs.zoomControl.setData({
                scale: 1,
                originX: 0,
                originY: 0,
                translateX: 0,
                translateY: 0,
            });
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
        onMoveTo(moveTo) {
            this.svgpanzoom.pan(moveTo);
        },
        onUpdatedCTM(CTM) {
            this.transform = CTM;
        },
        setScale(scale) {
            this.$store.commit("workflowState/setScale", scale);
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
            this.setScale(zoomLevel);
            this.svgpanzoom.zoom(zoomLevel);
        },
        registerSvgPanZoom(svgpanzoom) {
            this.svgpanzoom = svgpanzoom;
        },
        onPanContainer(e) {
            this.svgpanzoom.panBy({ x: e.data.deltaX, y: e.data.deltaY });
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
        zoomLevel() {
            return this.$store.getters["workflowState/getScale"]();
        },
        activeNodeId() {
            return this.$store.getters["workflowState/getActiveNode"]();
        },
        connections() {
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
    beforeDestroy() {
        this.svgpanzoom.destroy();
    },
};
</script>
