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
        }
    },
    methods: {
        onDestroy() {
            this.node.destroy();
        },
        onClone() {
            this.node.clone();
        }
    }
};
</script>
