<template>
    <div>
        <div class="toolFormTitle unselectable clearfix">
            <i :class="iconClass" />
            <span class="node-title">{{ title }}</span>
            <span class="sr-only">&nbsp;Node</span>
            <div class="buttons float-right">
                <a
                    v-if="canClone"
                    class="fa-icon-button fa fa-files-o node-clone"
                    aria-label="clone node"
                    role="button"
                    href="#"
                    @click="onClone"
                />
                <a
                    v-if="isEnabled"
                    class="fa-icon-button fa fa-arrow-right"
                    aria-label="tool recommendations"
                    role="button"
                    title="Show recommended tools"
                    href="#"
                    @click="onGetRecommendations"
                />
                <a
                    class="fa-icon-button fa fa-times node-destroy"
                    aria-label="destroy node"
                    role="button"
                    href="#"
                    @click="onDestroy"
                />
            </div>
        </div>
        <div class="toolFormBody">
            <div>
                <loading-span message="Loading details" />
            </div>
        </div>
    </div>
</template>

<script>
import WorkflowIcons from "components/Workflow/icons";
import LoadingSpan from "components/LoadingSpan";
import { getDatatypes } from "./services";
import { getToolRecommendations } from "./utilities";
import WorkflowManager from "mvc/workflow/workflow-manager";

export default {
    components: {
        LoadingSpan
    },
    props: {
        id: {
            type: String
        },
        title: {
            type: String,
            default: "title"
        },
        type: {
            type: String,
            default: "tool"
        },
        node: {
            type: Object
        }
    },
    computed: {
        iconClass() {
            const iconType = WorkflowIcons[this.type];
            if (iconType) {
                return `icon fa ${iconType}`;
            }
            return null;
        },
        canClone() {
            return this.type != "subworkflow";
        },
        isEnabled () {
            console.log("Is recommendation enabled workflow: " + window.Galaxy.config.enable_tool_recommendations);
            let isToolRecommendations = window.Galaxy.config.enable_tool_recommendations;
            if (this.node.content_id !== undefined && (isToolRecommendations === true || isToolRecommendations === 'true')) {
                return true;
            }
            else {
                return false;
            }
        }
    },
    methods: {
        onDestroy() {
            this.node.destroy();
        },
        onClone() {
            this.node.clone();
        },
        onGetRecommendations() {
            console.log(this);
            getDatatypes().then(response => {
                const datatypes = response.datatypes;
                const datatypes_mapping = response.datatypes_mapping;
                let workflow = new WorkflowManager({ datatypes_mapping }, $("#canvas-container"));
                console.log(workflow);
                getToolRecommendations(this.node, workflow);
            });
        }
    }
};
</script>
