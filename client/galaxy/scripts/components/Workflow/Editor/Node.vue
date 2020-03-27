<template>
    <div>
        <div class="node-header unselectable clearfix">
            <b-button
                class="node-destroy py-0 float-right"
                variant="primary"
                size="sm"
                aria-label="clone node"
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
                @click="onGetRecommendations"
            >
                <i class="fa fa-arrow-right" />
            </b-button>
            <b-popover :target="popoverId" triggers="hover" placement="bottom">
                <WorkflowRecommendations :node="node" />
            </b-popover>
            <b-button
                v-if="canClone"
                class="node-clone py-0 float-right"
                variant="primary"
                size="sm"
                aria-label="clone node"
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
import LoadingSpan from "components/LoadingSpan";
import { getGalaxyInstance } from "app";
import WorkflowRecommendations from "components/Workflow/Editor/WorkflowRecommendations";

Vue.use(BootstrapVue);

export default {
    components: {
        LoadingSpan,
        WorkflowRecommendations,
    },
    props: {
        id: {
            type: String,
            default: null,
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
            return `popover-${this.id}`;
        },
        canClone() {
            return this.type != "subworkflow";
        },
        isEnabled() {
            const Galaxy = getGalaxyInstance();
            const isRecommendationEnabled = Galaxy.config.enable_tool_recommendations;
            if (isRecommendationEnabled === true || isRecommendationEnabled === "true") {
                return true;
            }
            return false;
        },
    },
    methods: {
        onDestroy() {
            this.node.destroy();
        },
        onClone() {
            this.node.clone();
        },
    },
};
</script>
