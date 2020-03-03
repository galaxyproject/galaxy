<template>
    <div>
        <div class="node-header unselectable clearfix">
            <span class="node-title">{{ title }}</span>
            <b-dropdown right no-caret class="float-right" toggle-class="py-0" offset="50" variant="info" size="sm">
                <template v-slot:button-content>
                    <i :class="iconClass" />
                </template>
                <b-dropdown-item
                    v-if="canClone"
                    aria-label="clone node"
                    role="button"
                    href="#"
                    class="node-clone"
                    @click="onClone"
                >
                    <span class="fa-icon-button fa fa-files-o" />
                    Duplicate
                </b-dropdown-item>
                <b-dropdown-item
                    aria-label="destroy node"
                    role="button"
                    href="#"
                    class="node-destroy"
                    @click="onDestroy"
                >
                    <span class="fa-icon-button fa fa-fw fa-trash" />
                    Remove
                </b-dropdown-item>
            </b-dropdown>
        </div>
        <div class="node-body">
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
