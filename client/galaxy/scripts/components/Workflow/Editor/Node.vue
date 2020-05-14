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
                @click="onDestroy"
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
                <WorkflowRecommendations :node="node" @onCreate="onCreate" />
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
import { getModule } from "./modules/services";
import LoadingSpan from "components/LoadingSpan";
import { getGalaxyInstance } from "app";
import WorkflowRecommendations from "components/Workflow/Editor/Recommendations";
import NodeInput from "./NodeInput";
import NodeOutput from "./NodeOutput";
import { ActiveOutputs } from "./modules/outputs";

Vue.use(BootstrapVue);

export default {
    components: {
        LoadingSpan,
        WorkflowRecommendations,
        NodeInput,
        NodeOutput,
    },
    props: {
        id: {
            type: Number,
            default: -1,
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
            default: "tool",
        },
        getManager: {
            type: Function,
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
        };
    },
    mounted() {
        this.manager = this.getManager();
        this.activeOutputs = new ActiveOutputs();
        this.element = this.$el;
        this.content_id = this.contentId;
    },
    computed: {
        title() {
            return this.label || this.name;
        },
        idString() {
            return `wf-node-step-${this.id}`;
        },
        hasInputs() {
            return Object.keys(this.inputs).length > 0;
        },
        hasOutputs() {
            return Object.keys(this.outputs).length > 0;
        },
        showRule() {
            return this.hasInputs && this.hasOutputs;
        },
        showLoading() {
            return !this.hasInputs && !this.hasOutputs;
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
            this.manager.nodeChanged(this);
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
            this.manager.has_changes = true;
        },
        onCreate(toolId, event) {
            const requestData = {
                tool_id: toolId,
                type: "tool",
                _: "true",
            };
            getModule(requestData).then((response) => {
                const node = this.manager.createNode("tool", response.name, toolId);
                this.manager.setNode(node, response);
                this.popoverShow = false;
            });
        },
        onClone() {
            const copiedData = {
                name: this.name,
                label: this.label,
                annotation: this.annotation,
                post_job_actions: this.postJobActions,
            };
            const node = this.manager.createNode(this.type, this.name, this.content_id);
            const requestData = {
                type: this.type,
                tool_id: this.content_id,
                tool_state: this.tool_state,
            };
            getModule(requestData).then((response) => {
                const newData = Object.assign({}, response, copiedData);
                this.manager.setNode(node, newData);
            });
        },
        onDestroy() {
            Object.values(this.inputTerminals).forEach((t) => {
                t.destroy();
            });
            Object.values(this.outputTerminals).forEach((t) => {
                t.destroy();
            });
            this.manager.removeNode(this);
            this.element.remove();
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
        setData(data) {
            this.type = data.type || this.type;
            this.name = data.name;
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
            this.inputs = data.inputs.slice();
            this.outputs = data.outputs.slice();
            this.activeOutputs.initialize(this.outputs, data.workflow_outputs);
            Vue.nextTick(() => {
                this.manager.nodeChanged(this);
            });
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
                    // Remove the rendered output terminal
                    this.outputTerminals[name].$el.remove();
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

            // removes output from list of workflow outputs
            this.activeOutputs.updateOutputs(outputNames);

            // trigger legacy events
            Vue.nextTick(() => {
                this.manager.nodeChanged(this);
                this.onRedraw();
            });
        },
        labelOutput(output, label) {
            return this.activeOutputs.labelOutput(output, label);
        },
        changeOutputDatatype(output, datatype) {
            if (datatype === "__empty__") {
                datatype = null;
            }
            const outputName = output.name;
            const outputTerminal = this.outputTerminals[outputName];
            outputTerminal.force_datatype = datatype;
            output.force_datatype = datatype;
            if (datatype) {
                this.postJobActions["ChangeDatatypeAction" + outputName] = {
                    action_arguments: { newtype: datatype },
                    action_type: "ChangeDatatypeAction",
                    output_name: outputName,
                };
            } else {
                delete this.postJobActions["ChangeDatatypeAction" + outputName];
            }
            this.onChange();
            outputTerminal.destroyInvalidConnections();
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
