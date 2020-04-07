<template>
    <div :node-label="label">
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
        <b-alert v-if="!!error" variant="danger" show class="node-error">
            {{ error }}
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
            />
            <div v-if="showRule" class="rule" />
            <node-output
                v-for="output in outputs"
                :key="output.name"
                :output="output"
                :get-node="getNode"
                :get-manager="getManager"
                @onAdd="onAddOutput"
            />
        </div>
    </div>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import WorkflowIcons from "components/Workflow/icons";
import { getModule } from "./services";
import LoadingSpan from "components/LoadingSpan";
import { getGalaxyInstance } from "app";
import WorkflowRecommendations from "components/Workflow/Editor/Recommendations";
import { Node } from "mvc/workflow/workflow-node";
import NodeInput from "./NodeInput";
import NodeOutput from "./NodeOutput";

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
            type: String,
            default: "",
        },
        title: {
            type: String,
            default: "title",
        },
        type: {
            type: String,
            default: "tool",
        },
        f: {
            type: HTMLDivElement,
            default: null,
        },
        nodeId: {
            type: String,
            default: "",
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
            error: null,
            label: null,
            config_form: {},
            content_id: null
        };
    },
    mounted() {
        const manager = this.getManager();
        this.node = new Node(manager, { element: this.f });
        this.node.on("init", (data) => {
            this.setData(data);
            this.inputs = data.inputs.slice();
            this.outputs = data.outputs.slice();
            Vue.nextTick(() => {
                this.node.input_terminals = this.inputTerminals;
                this.node.output_terminals = this.outputTerminals;
                manager.node_changed(this.node);
            });
        });
        this.node.on("update", (data) => {
            // Identify unused outputs which existed previously
            var unused_outputs = [];
            this.outputs.forEach(({ name }) => {
                let unused = true;
                for (const existing in data.outputs) {
                    if (existing.name == name) {
                        unused = false;
                        break;
                    }
                }
                if (unused) {
                    unused_outputs.push(name);
                }
            });

            // Remove the unused outputs
            unused_outputs.forEach((unused_output) => {
                // Remove the noodle connectors
                this.outputTerminals[unused_output].connectors.forEach((x) => {
                    if (x) {
                        x.destroy();
                    }
                });
                // Remove the rendered output terminal
                this.outputTerminals[unused_output].remove();
                // Remove the reference to the output and output terminal
                delete this.outputTerminals[unused_output];
                delete this.node.output_terminals[unused_output];
            });

            // Add or update remaining outputs
            data.outputs.forEach((output) => {
                //this.outputs.push(output);
                if (!this.outputTerminals[output.name]) {
                    // add data output if it does not yet exist
                    this.outputs.push(output);
                } else {
                    // the output already exists, but the output formats may have changed.
                    // Therefore we update the datatypes and destroy invalid connections.
                    this.outputTerminals[output.name].datatypes = output.extensions;
                    this.outputTerminals[output.name].force_datatype = output.force_datatype;
                    if (this.type == "parameter_input") {
                        this.outputTerminals[output.name].attributes.type = output.type;
                    }
                    this.outputTerminals[output.name].optional = output.optional;
                    this.outputTerminals[output.name].destroyInvalidConnections();
                    this.node.output_terminals = this.outputTerminals;
                }
            });
            this.setData(data);

            /*$.each(node.workflow_outputs, (i, wf_output) => {
                if (wf_output && !node.output_terminals[wf_output.output_name]) {
                    node.workflow_outputs.splice(i, 1); // removes output from list of workflow outputs
                }
            });
            if ("post_job_actions" in data) {
                // Won't be present in response for data inputs
                var pja_in = data.post_job_actions;
                this.post_job_actions = pja_in ? pja_in : {};
            }
            this.nodeView.renderErrors();

            // Update input rows
            var newTerminals = {};
            _.each(data.inputs, (input) => {
                const terminal = this.input_terminals[input.name];
                if (!terminal) {
                    newTerminals[input.name] = this.nodeView.addDataInput(input);
                } else {
                    newTerminals[input.name] = terminal;
                    terminal.update(input);
                    terminal.destroyInvalidConnections();
                }
            });
            // Cleanup any leftover terminals
            _.each(_.difference(_.values(this.input_terminals), _.values(newTerminals)), (unusedTerminals) => {
                unusedTerminals.destroy();
            });
            this.input_terminals = newTerminals;
            this.nodeView.render();

            // In general workflow editor assumes tool outputs don't change in # or
            // type (not really valid right?) but adding special logic here for
            // data collection input parameters that can have their collection
            // change.
            var data_outputs = data.outputs;
            if (data_outputs.length == 1 && "collection_type" in data_outputs[0]) {
                // TODO
                //this.nodeView.updateDataOutput(data_outputs[0]);
                //var outputTerminal = this.nodeView.node.output_terminals[output.name];
                //outputTerminal.update(output);
            }

            // Won't be present in response for data inputs
            this.workflow_outputs = data.workflow_outputs || [];

            // If active, reactivate with new config_form
            this.markChanged();
            this.redraw();*/
        });
        this.error = this.node.errors;
    },
    computed: {
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
            return `popover-${this.nodeId}`;
        },
        canClone() {
            return this.type != "subworkflow";
        },
        isEnabled() {
            return getGalaxyInstance().config.enable_tool_recommendations;
        },
    },
    methods: {
        onAddInput(input, terminal) {
            /*const oldterminal = this.node.input_terminals[input.name];
            if (oldterminal) {
                oldterminal.update(input.name);
                oldterminal.destroyInvalidConnections();
                return;
            }*/
            this.inputTerminals[input.name] = terminal;
        },
        onAddOutput(output, terminal) {
            /*const oldterminal = this.node.input_terminals[input.name];
            if (oldterminal) {
                oldterminal.update(input.name);
                oldterminal.destroyInvalidConnections();
                return;
            }*/
            this.outputTerminals[output.name] = terminal;
        },
        onDestroy() {
            this.node.destroy();
        },
        onClone() {
            this.node.clone();
        },
        onCreate(toolId, event) {
            const requestData = {
                tool_id: toolId,
                type: "tool",
                _: "true",
            };
            getModule(requestData).then((response) => {
                var node = this.node.app.create_node("tool", response.name, toolId);
                this.node.app.set_node(node, response);
                this.popoverShow = false;
            });
        },
        getNode() {
            return this.node;
        },
        setData(data) {
            this.type = data.type;
            this.name = data.name;
            this.config_form = data.config_form;
            this.tool_state = data.tool_state;
            this.errors = data.errors;
            this.annotation = data.annotation;
            this.tooltip = data.tooltip ? data.tooltip : "";
            this.post_job_actions = data.post_job_actions ? data.post_job_actions : {};
            this.label = data.label;
            this.uuid = data.uuid;
            this.workflow_outputs = data.workflow_outputs ? data.workflow_outputs : [];
            if (this.type === "tool" && this.config_form) {
                this.node.tool_version = this.config_form.version;
                this.node.content_id = this.config_form.id;
            }
        }
    },
};
</script>
