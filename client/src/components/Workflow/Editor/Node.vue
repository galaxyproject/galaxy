<template>
    <draggable-wrapper
        :position="step.position || defaultPosition"
        :zoom="canvasManager.zoomLevel"
        @updatePosition="onUpdatePosition"
        @click="makeActive"
        :id="idString"
        :name="name"
        :node-label="label"
        :class="classes"
        :style="style">
        <div class="node-header unselectable clearfix">
            <b-button
                v-b-tooltip.hover
                class="node-destroy py-0 float-right"
                variant="primary"
                size="sm"
                aria-label="destroy node"
                title="Remove"
                @click="onRemove">
                <i class="fa fa-times" />
            </b-button>
            <b-button
                v-if="isEnabled"
                :id="popoverId"
                class="node-recommendations py-0 float-right"
                variant="primary"
                size="sm"
                aria-label="tool recommendations">
                <i class="fa fa-arrow-right" />
            </b-button>
            <b-popover :target="popoverId" triggers="hover" placement="bottom" :show.sync="popoverShow">
                <Recommendations
                    :get-node="getNode"
                    :get-manager="getManager"
                    :datatypes-mapper="datatypesMapper"
                    @onCreate="onCreate" />
            </b-popover>
            <b-button
                v-if="canClone"
                v-b-tooltip.hover
                class="node-clone py-0 float-right"
                variant="primary"
                size="sm"
                aria-label="clone node"
                title="Duplicate"
                @click="onClone">
                <i class="fa fa-files-o" />
            </b-button>
            <i :class="iconClass" />
            <span
                v-b-tooltip.hover
                title="Index of the step in the workflow run form. Steps are ordered by distance to the upper-left corner of the window; inputs are listed first."
                >{{ stepIndex }}:
            </span>
            <span class="node-title">{{ title }}</span>
        </div>
        <b-alert v-if="!!errors" variant="danger" show class="node-error">
            {{ errors }}
        </b-alert>
        <div v-else class="node-body">
            <loading-span v-if="showLoading" message="Loading details" />
            <node-input
                v-for="input in inputs"
                :key="input.name"
                :input="input"
                :get-node="getNode"
                :get-manager="getManager"
                :datatypes-mapper="datatypesMapper"
                :canvas-manager="canvasManager"
                @onAdd="onAddInput"
                @onRemove="onRemoveInput"
                @onDisconnect="onDisconnect"
                @onChange="onChange" />
            <div v-if="showRule" class="rule" />
            <node-output
                v-for="output in outputs"
                :key="output.name"
                :output="output"
                :post-job-actions="postJobActions"
                :get-node="getNode"
                :get-manager="getManager"
                :canvas-manager="canvasManager"
                @onAdd="onAddOutput"
                @onRemove="onRemoveOutput"
                @onToggle="onToggleOutput"
                @onChange="onChange" />
        </div>
    </draggable-wrapper>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import WorkflowIcons from "components/Workflow/icons";
import LoadingSpan from "components/LoadingSpan";
import { getGalaxyInstance } from "app";
import Recommendations from "components/Workflow/Editor/Recommendations";
import NodeInput from "./NodeInput";
import NodeOutput from "./NodeOutput";
import DraggableWrapper from "./Draggable";
import { ActiveOutputs } from "./modules/outputs";
Vue.use(BootstrapVue);

const OFFSET_RANGE = 100;

export default {
    components: {
        DraggableWrapper,
        LoadingSpan,
        Recommendations,
        NodeInput,
        NodeOutput,
    },
    props: {
        id: {
            type: String,
            default: "",
        },
        contentId: {
            type: String,
            default: "",
        },
        name: {
            type: String,
            default: "name",
        },
        type: {
            type: String,
            default: null,
        },
        step: {
            type: Object,
            default: null,
        },
        getManager: {
            type: Function,
            default: null,
        },
        getCanvasManager: {
            type: Function,
            default: null,
        },
        datatypesMapper: {
            type: Object,
            default: null,
        },
        activeNodeId: {
            type: String,
            default: null,
        },
    },
    data() {
        return {
            canvasManager: null,
            popoverShow: false,
            inputs: [],
            outputs: [],
            inputTerminals: {},
            outputTerminals: {},
            postJobActions: {},
            activeOutputs: null,
            errors: null,
            label: null,
            annotation: null,
            config_form: {},
            showLoading: true,
            highlight: false,
            scrolledTo: false,
            mouseDown: {},
        };
    },
    computed: {
        title() {
            return this.label || this.name;
        },
        idString() {
            return `wf-node-step-${this.id}`;
        },
        showRule() {
            return this.inputs.length > 0 && this.outputs.length > 0;
        },
        iconClass() {
            const iconType = WorkflowIcons[this.type];
            if (iconType) {
                return `icon fa fa-fw ${iconType}`;
            }
            return null;
        },
        popoverId() {
            return `popover-${this.id}`;
        },
        canClone() {
            return this.type != "subworkflow";
        },
        isEnabled() {
            return getGalaxyInstance().config.enable_tool_recommendations;
        },
        isInput() {
            return this.type == "data_input" || this.type == "data_collection_input" || this.type == "parameter_input";
        },
        stepIndex() {
            return parseInt(this.id) + 1;
        },
        isActive() {
            return this.id == this.activeNodeId;
        },
        classes() {
            const cssObj = {
                "workflow-node": true,
                "node-on-scroll-to": this.scrolledTo,
                "node-highlight": this.highlight || this.isActive,
            };
            if (this.isActive) {
                return { ...cssObj, "is-active": true };
            }
            return cssObj;
        },
        style() {
            if (isNaN(this.step.position?.top) || isNaN(this.step.position?.left)) {
                return this.defaultPosition;
            }
            return { top: this.step.position.top + "px", left: this.step.position.left + "px" };
        },
        defaultPosition() {
            console.log("defaultPosition fires");
            const p = document.getElementById("canvas-viewport");
            const o = document.getElementById("canvas-container");
            if (p && o) {
                const el = this.$el;
                const left =
                    -o.offsetLeft + (p.offsetWidth - el.offsetWidth) / 2 + this.offsetVaryPosition(OFFSET_RANGE);
                const top =
                    -o.offsetTop + (p.offsetHeight - el.offsetHeight) / 2 + this.offsetVaryPosition(OFFSET_RANGE);
                return { left, top };
            }
        },
    },
    created() {
        this.canvasManager = this.getCanvasManager();
        this.activeOutputs = new ActiveOutputs();
        this.element = this.$el;
        this.content_id = this.contentId;
        // initialize node data
        this.$emit("onAdd", this);
        if (this.step.config_form) {
            this.initData(this.step);
        } else {
            this.$emit("onUpdate", this);
        }
    },

    methods: {
        onUpdatePosition(position) {
            const newStep = { ...this.step, position };
            this.$emit("onUpdateStep", newStep.id, newStep);
        },
        onMouseDown(e) {
            this.mouseDown = { offsetX: e.offsetX, offsetY: e.offsetY };
            console.log("mouseDownOffset", this.mouseDown);
        },
        onDrag(e) {
            const left = this.step.position.left + (e.offsetX - this.mouseDown.offsetX) / this.canvasManager.canvasZoom;
            const top = this.step.position.top + (e.offsetY - this.mouseDown.offsetY) / this.canvasManager.canvasZoom;
            const newStep = { ...this.step, position: { left, top } };
            console.log({ left, top, e });
            this.$emit("onUpdateStep", newStep.id, newStep);
        },
        onDragEnd(e) {
            // this.$emit("onChange");
            // this.canvasManager.drawOverview();
            console.log("end");
        },
        onChange() {
            this.$emit("onChange");
        },
        onAddInput(input, terminal) {
            this.inputTerminals[input.name] = terminal;
            this.onRedraw();
        },
        onRemoveInput(input) {
            delete this.inputTerminals[input.name];
            this.onRedraw();
        },
        onDisconnect(inputName) {
            this.$emit("onDisconnect", this.id, inputName);
        },
        onAddOutput(output, terminal) {
            this.outputTerminals[output.name] = terminal;
            this.onRedraw();
        },
        onRemoveOutput(output) {
            delete this.outputTerminals[output.name];
            this.onRedraw();
        },
        onToggleOutput(name) {
            this.activeOutputs.toggle(name);
            this.$emit("onChange");
        },
        onCreate(contentId, name) {
            this.$emit("onCreate", contentId, name);
            this.popoverShow = false;
        },
        onClone() {
            this.$emit("onClone", this);
        },
        onRemove() {
            Object.values(this.inputTerminals).forEach((t) => {
                t.destroy();
            });
            Object.values(this.outputTerminals).forEach((t) => {
                t.destroy();
            });
            this.activeOutputs.filterOutputs([]);
            this.$emit("onRemove", this.id);
        },
        onRedraw() {
            Object.values(this.inputTerminals).forEach((t) => {
                t.redraw();
            });
            Object.values(this.outputTerminals).forEach((t) => {
                t.redraw();
            });
        },
        getNode() {
            return this;
        },
        setNode(data) {
            this.initData(data);
            this.$emit("onChange");
            this.$emit("onActivate", this.id);
        },
        setAnnotation(annotation) {
            this.annotation = annotation;
            this.$emit("onChange");
        },
        setLabel(label) {
            this.label = label;
            this.$emit("onChange");
        },
        setData(data) {
            this.content_id = data.content_id;
            this.tool_state = data.tool_state;
            this.errors = data.errors;
            this.tooltip = data.tooltip || "";
            this.inputs = data.inputs ? data.inputs.slice() : [];
            this.outputs = data.outputs ? data.outputs.slice() : [];
            const outputNames = this.outputs.map((output) => output.name);
            this.activeOutputs.initialize(this.outputs, data.workflow_outputs);
            this.activeOutputs.filterOutputs(outputNames);
            // data coming from the workflow editor API has post job actions,
            // data coming from the build_module call does not (and should not)
            this.postJobActions = data.post_job_actions || this.postJobActions;
            this.config_form = data.config_form;
        },
        initData(data) {
            this.uuid = data.uuid;
            this.annotation = data.annotation;
            this.label = data.label;
            this.setData(data);
            this.showLoading = false;
        },
        onScrollTo() {
            this.scrolledTo = true;
            setTimeout(() => {
                this.scrolledTo = false;
            }, 2000);
        },
        onHighlight() {
            this.highlight = true;
        },
        onUnhighlight() {
            this.highlight = false;
        },
        makeActive() {
            console.log("Clicked");
            this.$emit("onActivate", this.id);
        },
        offsetVaryPosition(offsetRange) {
            return Math.floor(Math.random() * offsetRange);
        },
    },
};
</script>
