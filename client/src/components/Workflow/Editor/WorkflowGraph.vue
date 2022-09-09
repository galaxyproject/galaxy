<template>
    <div id="workflow-canvas" class="unified-panel-body workflow-canvas">
        <ZoomControl :zoom-level="zoomLevel" @onZoom="onZoomButton" />
        <div class="canvas-viewport" @dragover.prevent @drop.prevent>
            <div id="canvas-container" ref="el">
                <Draggable style="width: 100%; height: 100%" @move="onPanContainer" :apply-scale="false">
                    <SvgPanZoom
                        style="width: 100%; height: 100%"
                        :minZoom="0.1"
                        :panEnabled="false"
                        :zoomEnabled="true"
                        :controlIconsEnabled="false"
                        :fit="false"
                        :center="false"
                        :on-zoom="onZoom"
                        :onUpdatedCTM="onUpdatedCTM"
                        @svgpanzoom="registerSvgPanZoom">
                        <svg class="canvas-svg" width="100%" height="100%" ref="svg">
                            <g class="zoomable">
                                <raw-connector v-if="draggingConnection" :position="draggingConnection"></raw-connector>
                                <terminal-connector
                                    v-for="connection in connections"
                                    :key="connection.id"
                                    :connection="connection"></terminal-connector>
                            </g>
                        </svg>
                    </SvgPanZoom>
                    <div class="nodeArea" :style="style">
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
                            :root-offset="position"
                            @pan-by="onPan"
                            @stopDragging="onStopDragging"
                            @onDragConnector="onDragConnector"
                            @onActivate="onActivate"
                            @onRemove="onRemove"
                            v-on="$listeners" />
                    </div>
                </Draggable>
            </div>
        </div>
        <Minimap :nodes="nodes" :steps="steps" :root-offset="position" :scale="zoomLevel" :pan="currentPan" />
    </div>
</template>
<script>
import ZoomControl from "./ZoomControl";
import WorkflowNode from "./Node";
import RawConnector from "./Connector";
import TerminalConnector from "./TerminalConnector";
import Draggable from "./Draggable.vue";
import Minimap from "./Minimap.vue";
import SvgPanZoom from "vue-svg-pan-zoom";
import { reactive, ref } from "vue";
import { useElementBounding } from "@vueuse/core";

export default {
    setup() {
        const el = ref(null);
        const position = reactive(useElementBounding(el));
        return { el, position };
    },
    components: {
        Draggable,
        RawConnector,
        SvgPanZoom,
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
        onPan(pan) {
            this.svgpanzoom.panBy(pan);
        },
        onPanContainer(e) {
            this.svgpanzoom.panBy({ x: e.data.deltaX, y: e.data.deltaY });
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
                return `transform: matrix(${this.transform.a}, ${this.transform.b}, ${this.transform.c}, ${this.transform.d}, ${this.transform.e}, ${this.transform.f})`;
            }
        },
        currentPan() {
            if (this.transform) {
                return { x: this.transform.e, y: this.transform.f };
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
    beforeDestroy() {
        this.svgpanzoom.destroy();
    },
};
</script>
