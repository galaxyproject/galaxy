<template>
    <div :class="['callout-terminal', outputName]" @click="onToggle">
        <i :class="['mark-terminal', activeClass]" />
    </div>
</template>

<script>

export default {
    props: {
        node: {
            type: Object,
            default: null,
        },
        outputName: {
            type: String,
            required: true,
        },
        manager: {
            type: Object,
            required: true,
        }
    },
    computed: {
        activeClass() {
            if (this.node.isWorkflowOutput(this.outputName)) {
                return "mark-terminal-active";
            }
            return "";
        },
    },
    methods: {
        onToggle() {
            if (this.node.isWorkflowOutput(this.outputName)) {
                this.node.removeWorkflowOutput(this.outputName);
            } else {
                this.node.addWorkflowOutput(this.outputName);
            }
            this.manager.has_changes = true;
        }
    }
};
</script>
