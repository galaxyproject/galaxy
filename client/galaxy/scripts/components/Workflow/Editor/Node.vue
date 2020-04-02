<template>
    <div :node-label="node.label">
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
            inputTerminals: {},
            inputs: [],
            outputTerminals: {},
            outputs: [],
            error: null,
        }
    },
    mounted() {
        this.node = new Node(this.getManager(), { nodeVue: this, element: this.f });
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
    },
};
</script>
