<template>
    <div>
        <div class="toolFormTitle unselectable">
            <i :class="iconClass" />
            <span class="nodeTitle">
                {{ title }}
            </span>
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
            test
        </div>
    </div>
</template>

<script>
import WorkflowIcons from "mvc/workflow/workflow-icons";

export default {
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
            //node.destroy();
        },
        onClone() {
            //node.clone();
        }
    }
};
</script>
