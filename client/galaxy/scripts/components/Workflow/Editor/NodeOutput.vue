<template>
    <div class="form-row dataRow output-data-row">
        <div ref="terminal" class="terminal output-terminal" />
        <div v-if="showCallout" :class="['callout-terminal', outputName]" @click="onToggle">
            <i :class="['mark-terminal', activeClass]" />
        </div>
        {{ label }}
    </div>
</template>

<script>
export default {
    props: {
        output: {
            type: Object,
            default: null,
        },
        getNode: {
            type: Function,
            required: true,
        },
        getManager: {
            type: Function,
            required: true,
        },
    },
    computed: {
        activeClass() {
            const node = this.getNode();
            if (node.isWorkflowOutput(this.output.name)) {
                return "mark-terminal-active";
            }
            return "";
        },
        label() {
            return this.output.label || this.output.name;
        },
        showCallout() {
            const node = this.getNode();
            return ["tool", "subworkflow"].indexOf(node.type) >= 0;
        }
    },
    methods: {
        onToggle() {
            const node = this.getNode();
            const manager = this.getManager();
            const outputName = this.output.name;
            if (node.isWorkflowOutput(outputName)) {
                node.removeWorkflowOutput(outputName);
            } else {
                node.addWorkflowOutput(outputName);
            }
            manager.has_changes = true;
        },
    },
};
</script>
