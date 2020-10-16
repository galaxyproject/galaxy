<template>
    <div :id="idString" :name="name" :node-label="label" class="workflow-node">
        <div class="node-header unselectable clearfix">
            <b-button
                class="node-destroy py-0 float-right"
                variant="primary"
                size="sm"
                aria-label="destroy node"
                v-b-tooltip.hover
                title="Remove"
                @click="onRemove"
            >
                <i class="fa fa-times" />
            </b-button>
            <b-button
                :id="popoverId"
                v-if="isEnabled"
                class="node-recommendations py-0 float-right"
                variant="primary"
                size="sm"
                aria-label="tool recommendations"
            >
                <i class="fa fa-arrow-right" />
            </b-button>
            <b-popover :target="popoverId" triggers="hover" placement="bottom" :show.sync="popoverShow">
                <Recommendations
                    :get-node="getNode"
                    :get-manager="getManager"
                    :datatypes-mapper="datatypesMapper"
                    @onCreate="onCreate"
                />
            </b-popover>
            <b-button
                v-if="canClone"
                class="node-clone py-0 float-right"
                variant="primary"
                size="sm"
                aria-label="clone node"
                v-b-tooltip.hover
                title="Duplicate"
                @click="onClone"
            >
                <i class="fa fa-files-o" />
            </b-button>
            <i :class="iconClass" />
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
                @onAdd="onAddInput"
                @onChange="onChange"
            />
            <div v-if="showRule" class="rule" />
            <node-output
                v-for="output in outputs"
                :key="output.name"
                :output="output"
                :get-node="getNode"
                :get-manager="getManager"
                @onAdd="onAddOutput"
                @onToggle="onToggleOutput"
                @onChange="onChange"
            />
        </div>
    </div>
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
import { ActiveOutputs } from "./modules/outputs";
import { attachDragging } from "./modules/dragging";
Vue.use(BootstrapVue);

export default {
    components: {
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
    },
    data() {
        return {
            popoverShow: false,
            node: null,
            inputs: [],
            outputs: [],
            inputTerminals: {},
            outputTerminals: {},
            errors: null,
            label: null,
            config_form: {},
            showLoading: true,
        };
    },
    mounted() {
        this.canvasManager = this.getCanvasManager();
        this.activeOutputs = new ActiveOutputs();
        this.element = this.$el;
        this.content_id = this.contentId;

        // Set initial scroll position
        const step = this.step;
        const el = this.$el;
        if (step.position) {
            el.style.top = step.position.top + "px";
            el.style.left = step.position.left + "px";
        } else {
            const p = document.getElementById("canvas-viewport");
            const o = document.getElementById("canvas-container");
            if (p && o) {
                const left = -o.offsetLeft + (p.offsetWidth - el.offsetWidth) / 2;
                const top = -o.offsetTop + (p.offsetHeight - el.offsetHeight) / 2;
                el.style.top = `${top}px`;
                el.style.left = `${left}px`;
            }
        }

        // Attach node dragging events
        attachDragging(this.$el, {
            dragstart: () => {
                this.$emit("onActivate", this);
            },
            dragend: () => {
                this.$emit("onChange");
                this.canvasManager.drawOverview();
            },
            drag: (e, d) => {
                const o = document.getElementById("canvas-container");
                const el = this.$el;
                const rect = o.getBoundingClientRect();
                const left = (d.offsetX - rect.left) / this.canvasManager.canvasZoom;
                const top = (d.offsetY - rect.top) / this.canvasManager.canvasZoom;
                el.style.left = `${left}px`;
                el.style.top = `${top}px`;
                this.onRedraw();
            },
            dragclickonly: () => {
                this.$emit("onActivate", this);
            },
        });

        // initialize node data
        this.$emit("onAdd", this);
        if (this.step._complete) {
            this.initData(this.step);
            this.updateData(this.step);
        } else {
            this.$emit("onUpdate", this);
        }
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
    },
    methods: {
        onChange() {
            this.$emit("onChange");
        },
        onAddInput(input, terminal) {
            const existingTerminal = this.inputTerminals[input.name];
            if (existingTerminal) {
                existingTerminal.update(input);
                existingTerminal.destroyInvalidConnections();
            } else {
                this.inputTerminals[input.name] = terminal;
            }
        },
        onAddOutput(output, terminal) {
            const existingTerminal = this.outputTerminals[output.name];
            if (existingTerminal) {
                existingTerminal.update(output);
                existingTerminal.destroyInvalidConnections();
            } else {
                this.outputTerminals[output.name] = terminal;
            }
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
            this.activeOutputs.filterOutputs({});
            this.$emit("onRemove", this);
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
            data.workflow_outputs = data.outputs.map((o) => {
                return {
                    output_name: o.name,
                    label: o.label,
                };
            });
            this.initData(data);
            Vue.nextTick(() => {
                this.updateData(data);
                this.$emit("onActivate", this);
            });
        },
        setData(data) {
            this.config_form = data.config_form;
            this.tool_state = data.tool_state;
            this.errors = data.errors;
            this.annotation = data.annotation;
            this.tooltip = data.tooltip || "";
            this.postJobActions = data.post_job_actions || {};
            this.label = data.label;
            this.uuid = data.uuid;
        },
        initData(data) {
            this.setData(data);
            this.inputs = data.inputs ? data.inputs.slice() : [];
            this.outputs = data.outputs ? data.outputs.slice() : [];
            this.activeOutputs.initialize(this.outputs, data.workflow_outputs);
            this.$emit("onChange");
        },
        updateData(data) {
            this.setData(data);

            // Create a dictionary of all incoming outputs
            const outputNames = {};
            const outputIndex = {};
            data.outputs.forEach((output) => {
                const name = output.name;
                outputNames[name] = 1;
                outputIndex[name] = output;
            });

            // Identify unused outputs which existed previously
            for (let i = this.outputs.length - 1; i >= 0; i--) {
                const output = this.outputs[i];
                const name = output.name;
                if (!outputNames[name]) {
                    // Remove the noodle connectors
                    this.outputTerminals[name].connectors.forEach((x) => {
                        if (x) {
                            x.destroy();
                        }
                    });
                    // Remove the reference to the output and output terminal
                    delete this.outputTerminals[name];
                    this.outputs.splice(i, 1);
                } else {
                    // Output exists in both sources
                    outputNames[name] = 2;
                    // Update existing outputs with incoming output attributes
                    const outputIncoming = outputIndex[name];
                    Object.entries(outputIncoming).forEach(([key, newValue]) => {
                        Vue.set(output, key, newValue);
                    });
                }
            }

            // Add or update remaining outputs
            data.outputs.forEach((output) => {
                const terminal = this.outputTerminals[output.name];
                if (terminal) {
                    terminal.update(output);
                    terminal.destroyInvalidConnections();
                }
                if (outputNames[output.name] == 1) {
                    this.outputs.push(output);
                }
            });

            // Create a list of all current input names
            const inputNames = {};
            const inputIndex = {};
            data.inputs.forEach((input) => {
                const name = input.name;
                inputNames[name] = 1;
                inputIndex[name] = input;
            });

            // Identify unused inputs which existed previously
            for (let i = this.inputs.length - 1; i >= 0; i--) {
                const name = this.inputs[i].name;
                if (!inputNames[name] || inputIndex[name].input_type !== this.inputs[i].input_type) {
                    this.inputTerminals[name].destroy();
                    delete this.inputTerminals[name];
                    this.inputs.splice(i, 1);
                } else {
                    inputNames[name] = 2;
                }
            }

            // Add and update input rows
            data.inputs.forEach((input) => {
                const terminal = this.inputTerminals[input.name];
                if (terminal) {
                    terminal.update(input);
                    terminal.destroyInvalidConnections();
                }
                if (inputNames[input.name] == 1) {
                    this.inputs.push(input);
                }
            });

            this.inputs.forEach((input) => {
                // Update input terminal labels
                input.label = inputIndex[input.name].label;
            });

            // removes output from list of workflow outputs
            this.activeOutputs.filterOutputs(outputNames);

            // trigger legacy events
            Vue.nextTick(() => {
                this.onRedraw();
            });

            // emit change completion event
            this.showLoading = false;
            this.$emit("onChange");
        },
        labelOutput(outputName, label) {
            return this.activeOutputs.labelOutput(outputName, label);
        },
        changeOutputDatatype(outputName, datatype) {
            if (datatype === "__empty__") {
                datatype = null;
            }
            const outputTerminal = this.outputTerminals[outputName];
            if (datatype) {
                this.postJobActions["ChangeDatatypeAction" + outputName] = {
                    action_arguments: { newtype: datatype },
                    action_type: "ChangeDatatypeAction",
                    output_name: outputName,
                };
            } else {
                delete this.postJobActions["ChangeDatatypeAction" + outputName];
            }
            outputTerminal.destroyInvalidConnections();
            this.$emit("onChange");
        },
        makeActive() {
            this.element.classList.add("node-active");
        },
        makeInactive() {
            // Keep inactive nodes stacked from most to least recently active
            // by moving element to the end of parent's node list
            const element = this.element;
            ((p) => {
                p.removeChild(element);
                p.appendChild(element);
            })(element.parentNode);
            // Remove active class
            element.classList.remove("node-active");
        },
    },
};
</script>
