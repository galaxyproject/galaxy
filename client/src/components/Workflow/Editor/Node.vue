<template>
    <draggable-wrapper
        :id="idString"
        ref="el"
        :scale="scale"
        :root-offset="rootOffset"
        :name="name"
        :node-label="title"
        :class="classes"
        :style="style"
        @updatePosition="onUpdatePosition"
        @move="onMoveTo"
        @pan-by="onPanBy">
        <div class="node-header unselectable clearfix" @click="makeActive">
            <!-- clicking destroy shouldn't also trigger makeActive -->
            <b-button
                v-b-tooltip.hover
                class="node-destroy py-0 float-right"
                variant="primary"
                size="sm"
                aria-label="destroy node"
                title="Remove"
                @click.prevent.stop="onRemove">
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
        <b-alert v-if="!!errors" variant="danger" show class="node-error" @click="makeActive">
            {{ errors }}
        </b-alert>
        <div v-else class="node-body" @click="makeActive">
            <loading-span v-if="showLoading" message="Loading details" />
            <node-input
                v-for="input in inputs"
                :key="nodeIOKey(input.name, step.position)"
                :input="input"
                :get-node="getNode"
                :datatypes-mapper="datatypesMapper"
                :step-position="step.position"
                :root-offset="rootOffset"
                :parent-offset="position"
                v-on="$listeners"
                @onAdd="onAddInput"
                @onRemove="onRemoveInput"
                @onDisconnect="onDisconnect"
                @onChange="onChange" />
            <div v-if="showRule" class="rule" />
            <node-output
                v-for="output in outputs"
                :key="nodeIOKey(output.name, step.position)"
                :output="output"
                :post-job-actions="postJobActions"
                :get-node="getNode"
                :step-position="step.position"
                :root-offset="rootOffset"
                :parent-offset="position"
                v-on="$listeners"
                @stopDragging="onStopDragging"
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
import DraggableWrapper from "./DraggablePan";
import { ActiveOutputs } from "./modules/outputs";
import { computed, inject, reactive, ref } from "vue";
import { useElementBounding } from "@vueuse/core";

Vue.use(BootstrapVue);

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
            type: Number,
            required: true,
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
        datatypesMapper: {
            type: Object,
            default: null,
        },
        activeNodeId: {
            type: Number,
            required: false,
        },
        rootOffset: {
            type: Object,
            required: true,
        },
        scale: {
            type: Number,
        },
    },
    setup(props) {
        const nodeIOKey = (key, position) => key + position?.left + position?.right;
        const el = ref(null);
        const position = reactive(useElementBounding(el, { windowResize: false }));
        const transform = inject("transform");
        const postJobActions = computed(() => props.step.post_job_actions || {});
        return { el, position, transform, nodeIOKey, postJobActions };
    },
    data() {
        return {
            popoverShow: false,
            inputs: [],
            outputs: [],
            inputTerminals: {},
            outputTerminals: {},
            activeOutputs: null,
            errors: null,
            config_form: {},
            showLoading: true,
            highlight: false,
            scrolledTo: false,
            offset: {
                x: 0,
                y: 0,
            },
        };
    },
    computed: {
        title() {
            return this.step.label || this.step.name;
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
    },
    created() {
        this.$store.commit("workflowState/setNode", this);
        this.activeOutputs = new ActiveOutputs();
        this.content_id = this.contentId;
        // initialize node data
        if (this.step.config_form) {
            this.initData(this.step);
        } else {
            this.$emit("onUpdate", this);
        }
    },
    beforeDestroy() {
        this.$store.commit("workflowState/deleteNode", this.id);
    },
    methods: {
        onMoveTo(position, event) {
            this.onUpdatePosition({
                top: position.y,
                left: position.x,
            });
        },
        onPanBy(panBy) {
            this.$emit("pan-by", panBy);
        },
        onStopDragging() {
            this.$emit("stopDragging");
        },
        onUpdatePosition(position) {
            this.$emit("onUpdateStepPosition", this.step.id, position);
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
            this.config_form = data.config_form;
        },
        initData(data) {
            this.uuid = data.uuid;
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
            this.$emit("onActivate", this.id);
        },
    },
};
</script>
