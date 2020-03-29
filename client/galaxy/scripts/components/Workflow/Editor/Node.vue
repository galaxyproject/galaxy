<template>
    <div>
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
        <div class="node-body">
            <div>
                <loading-span message="Loading details" />
            </div>
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

Vue.use(BootstrapVue);

export default {
    components: {
        LoadingSpan,
        WorkflowRecommendations,
    },
    data() {
        return {
            popoverShow: false,
        };
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
        node: {
            type: Object,
            default: null,
        },
        nodeId: {
            type: String,
            default: "",
        },
    },
    computed: {
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
    },
};
</script>
