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
import $ from "jquery";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import WorkflowIcons from "components/Workflow/icons";
import { getModule } from "./services";
import LoadingSpan from "components/LoadingSpan";
import { getGalaxyInstance } from "app";
import WorkflowRecommendations from "components/Workflow/Editor/Recommendations";
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
            type: Number,
            default: -1,
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
            workflowOutputs: [],
            error: null,
            label: null,
            config_form: {},
            content_id: null,
        };
    },
    mounted() {
        this.manager = this.getManager();
        this.node = this;
        this.element = $(this.f);
        this.input_terminals = {};
        this.output_terminals = {};
        this.errors = null;
        this.workflow_outputs = [];
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
            console.log(output.name);
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
        redraw() {
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
            this.type = data.type;
            this.name = data.name;
            this.config_form = data.config_form;
            this.tool_state = data.tool_state;
            this.errors = data.errors;
            this.annotation = data.annotation;
            this.tooltip = data.tooltip ? data.tooltip : "";
            this.postJobActions = data.post_job_actions || {};
            this.label = data.label;
            this.uuid = data.uuid;
            this.workflowOutputs = data.workflow_outputs || [];
            if (this.type === "tool" && this.config_form) {
                this.node.tool_version = this.config_form.version;
                this.node.content_id = this.config_form.id;
            }
        },
        initData(data) {
            this.setData(data);
            this.inputs = data.inputs.slice();
            this.outputs = data.outputs.slice();
            Vue.nextTick(() => {
                this.node.input_terminals = this.inputTerminals;
                this.node.output_terminals = this.outputTerminals;
                this.manager.node_changed(this.node);
            });
        },
        updateData(data) {
            this.setData(data);

            // Create a list of all current output names
            const outputNames = {};
            data.outputs.forEach(({ name }) => {
                outputNames[name] = true;
            });

            // Identify unused outputs which existed previously
            for (let i = this.outputs.length - 1; i >= 0; i--) {
                const name = this.outputs[i].name;
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
                    delete this.node.output_terminals[name];
                    this.outputs.splice(i, 1);
                }
            }

            // Add or update remaining outputs
            data.outputs.forEach((output) => {
                const terminal = this.outputTerminals[output.name];
                if (!terminal) {
                    this.outputs.push(output);
                } else {
                    // the output already exists, but the output formats may have changed.
                    // Therefore we update the datatypes and destroy invalid connections.
                    terminal.datatypes = output.extensions;
                    terminal.force_datatype = output.force_datatype;
                    if (this.type == "parameter_input") {
                        terminal.attributes.type = output.type;
                    }
                    terminal.optional = output.optional;
                    terminal.destroyInvalidConnections();
                }
            });

            // Create a list of all current input names
            const inputNames = {};
            data.inputs.forEach(({ name }) => {
                inputNames[name] = true;
            });

            // Identify unused inputs which existed previously
            for (let i = this.inputs.length - 1; i >= 0; i--) {
                const name = this.inputs[i].name;
                if (!inputNames[name]) {
                    this.inputTerminals[name].destroy();
                    delete this.inputTerminals[name];
                    delete this.node.input_terminals[name];
                    this.inputs.splice(i, 1);
                }
            }

            // Add and update input rows
            data.inputs.forEach((input) => {
                const terminal = this.inputTerminals[input.name];
                if (!terminal) {
                    this.inputs.push(input);
                } else {
                    terminal.update(input);
                    terminal.destroyInvalidConnections();
                }
            });

            // removes output from list of workflow outputs
            this.workflowOutputs.forEach((wf_output, i) => {
                if (!this.outputTerminals[wf_output.output_name]) {
                    this.workflowOutputs.splice(i, 1);
                }
            });

            Vue.nextTick(() => {
                this.node.workflow_outputs = this.workflowOutputs;
                this.node.input_terminals = this.inputTerminals;
                this.node.output_terminals = this.outputTerminals;
                this.manager.node_changed(this.node);
                this.redraw();
            });

            /* In general workflow editor assumes tool outputs don't change in # or
            // type (not really valid right?) but adding special logic here for
            // data collection input parameters that can have their collection
            // change.
            var data_outputs = data.outputs;
            if (data_outputs.length == 1 && "collection_type" in data_outputs[0]) {
                // TODO
                //this.nodeView.updateDataOutput(data_outputs[0]);
                //var outputTerminal = this.nodeView.node.output_terminals[output.name];
                //outputTerminal.update(output);
            }*/
        },
        getWorkflowOutput(outputName) {
            /*return _.findWhere(this.workflowOutputs, {
                output_name: outputName,
            });*/
        },
        isWorkflowOutput(outputName) {
            return this.getWorkflowOutput(outputName) !== undefined;
        },
        removeWorkflowOutput(outputName) {
            while (this.isWorkflowOutput(outputName)) {
                //const target = this.getWorkflowOutput(outputName);
                //this.workflowOutputs.splice(_.indexOf(this.workflowOutputs, target), 1);
            }
        },
        addWorkflowOutput(outputName, label) {
            if (!this.isWorkflowOutput(outputName)) {
                var output = { output_name: outputName };
                if (label) {
                    output.label = label;
                }
                this.workflowOutputs.push(output);
                return true;
            }
            return false;
        },
        markWorkflowOutput(outputName) {
            //var callout = $(this.element).find(`.callout-terminal.${outputName.replace(/(?=[()])/g, "\\")}`);
            //callout.find("icon").addClass("mark-terminal-active");
        },
        labelWorkflowOutput(outputName, label) {
            var changed = false;
            var oldLabel = null;
            if (this.isWorkflowOutput(outputName)) {
                var workflowOutput = this.getWorkflowOutput(outputName);
                oldLabel = workflowOutput.label;
                workflowOutput.label = label;
                changed = oldLabel != label;
            } else {
                changed = this.addWorkflowOutput(outputName, label);
            }
            if (changed) {
                this.app.updateOutputLabel(oldLabel, label);
                this.markChanged();
            }
            return changed;
        },
        changeOutputDatatype(outputName, datatype) {
            const output_terminal = this.output_terminals[outputName];
            const output = this.nodeView.outputViews[outputName].output;
            output_terminal.force_datatype = datatype;
            output.force_datatype = datatype;
            if (datatype) {
                this.post_job_actions["ChangeDatatypeAction" + outputName] = {
                    action_arguments: { newtype: datatype },
                    action_type: "ChangeDatatypeAction",
                    output_name: outputName,
                };
            } else {
                delete this.post_job_actions["ChangeDatatypeAction" + outputName];
            }
            this.markChanged();
            output_terminal.destroyInvalidConnections();
        },
        connectedOutputTerminals() {
            return this._connectedTerminals(this.output_terminals);
        },
        _connectedTerminals(terminals) {
            var connectedTerminals = [];
            $.each(terminals, (_, t) => {
                if (t.connectors.length > 0) {
                    connectedTerminals.push(t);
                }
            });
            return connectedTerminals;
        },
        hasConnectedOutputTerminals() {
            // return this.connectedOutputTerminals().length > 0; <- optimized this
            var outputTerminals = this.output_terminals;
            for (var outputName in outputTerminals) {
                if (outputTerminals[outputName].connectors.length > 0) {
                    return true;
                }
            }
            return false;
        },
        connectedMappedInputTerminals() {
            return this._connectedMappedTerminals(this.input_terminals);
        },
        hasConnectedMappedInputTerminals() {
            // return this.connectedMappedInputTerminals().length > 0; <- optimized this
            var inputTerminals = this.input_terminals;
            for (var inputName in inputTerminals) {
                var inputTerminal = inputTerminals[inputName];
                if (inputTerminal.connectors.length > 0 && inputTerminal.isMappedOver()) {
                    return true;
                }
            }
            return false;
        },
        _connectedMappedTerminals(terminals) {
            var mapped_outputs = [];
            $.each(terminals, (_, t) => {
                var mapOver = t.mapOver;
                if (mapOver.isCollection) {
                    if (t.connectors.length > 0) {
                        mapped_outputs.push(t);
                    }
                }
            });
            return mapped_outputs;
        },
        mappedInputTerminals() {
            return this._mappedTerminals(this.input_terminals);
        },
        _mappedTerminals(terminals) {
            var mappedTerminals = [];
            $.each(terminals, (_, t) => {
                var mapOver = t.mapOver;
                if (mapOver.isCollection) {
                    mappedTerminals.push(t);
                }
            });
            return mappedTerminals;
        },
        hasMappedOverInputTerminals() {
            var found = false;
            /*_.each(this.input_terminals, (t) => {
                var mapOver = t.mapOver;
                if (mapOver.isCollection) {
                    found = true;
                }
            });*/
            return found;
        },
        clone() {
            var copiedData = {
                name: this.name,
                label: this.label,
                annotation: this.annotation,
                post_job_actions: this.post_job_actions,
            };
            var node = this.app.create_node(this.type, this.name, this.content_id);
            /*Utils.request({
                type: "POST",
                url: `${getAppRoot()}api/workflows/build_module`,
                data: {
                    type: this.type,
                    tool_id: this.content_id,
                    tool_state: this.tool_state,
                },
                success: (data) => {
                    var newData = Object.assign({}, data, copiedData);
                    node.init_field_data(newData);
                    Vue.nextTick(() => {
                        node.update_field_data(newData);
                        this.app.activate_node(node);
                    });
                },
            });*/
        },
        destroy() {
            /*$.each(this.input_terminals, (k, t) => {
                t.destroy();
            });
            $.each(this.output_terminals, (k, t) => {
                t.destroy();
            });*/
            this.app.remove_node(this);
            //$(this.element).remove();
        },
        make_active() {
            //$(this.element).addClass("node-active");
        },
        make_inactive() {
            // Keep inactive nodes stacked from most to least recently active
            // by moving element to the end of parent's node list
            var element = this.element.get(0);
            ((p) => {
                p.removeChild(element);
                p.appendChild(element);
            })(element.parentNode);
            // Remove active class
            //$(element).removeClass("node-active");
        },
        init_field_data(data) {
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
                this.tool_version = this.config_form.version;
                this.content_id = this.config_form.id;
            }
            this.initData(data);
        },
        update_field_data(data) {
            this.updateData(data);
        },
        markChanged() {
            this.manager.node_changed(this);
        }
    }
};
</script>
