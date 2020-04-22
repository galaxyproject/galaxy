<template>
    <div class="form-row dataRow output-data-row">
        <div v-if="showCallout" :class="['callout-terminal', output.name]" @click="onToggle">
            <i :class="['mark-terminal', activeClass && 'mark-terminal-active']" />
        </div>
        {{ label }}
        <div ref="terminal" class="terminal output-terminal" />
    </div>
</template>

<script>
import Terminals from "mvc/workflow/workflow-terminals";
import TerminalViews from "mvc/workflow/workflow-view-terminals";

export default {
    props: {
        output: {
            type: Object,
            required: true,
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
    data() {
        return {
            activeClass: false,
        };
    },
    computed: {
        label() {
            return this.output.label || this.output.name;
        },
        showCallout() {
            const node = this.getNode();
            return ["tool", "subworkflow"].indexOf(node.type) >= 0;
        },
    },
    mounted() {
        const output = this.output;
        if (output.collection) {
            const collection_type = output.collection_type;
            const collection_type_source = output.collection_type_source;
            this.terminal = new Terminals.OutputCollectionTerminal({
                element: this.$refs.terminal,
                collection_type: collection_type,
                collection_type_source: collection_type_source,
                datatypes: output.extensions,
                force_datatype: output.force_datatype,
                optional: output.optional,
            });
        } else if (output.parameter) {
            this.terminal = new Terminals.OutputParameterTerminal({
                element: this.$refs.terminal,
                type: output.type,
                optional: output.optional,
            });
        } else {
            this.terminal = new Terminals.OutputTerminal({
                element: this.$refs.terminal,
                datatypes: output.extensions,
                force_datatype: output.force_datatype,
                optional: output.optional,
            });
        }
        this.$emit("onAdd", this.output, this.terminal);
        new TerminalViews.OutputTerminalView(this.getManager(), {
            node: this.getNode(),
            output: output,
            el: this.$refs.terminal,
            terminal: this.terminal,
        });
        const node = this.getNode();
        if (node.activeOutputs.exists(this.output.name)) {
            this.activeClass = true;
        }
    },
    methods: {
        onToggle() {
            const node = this.getNode();
            const manager = this.getManager();
            const outputName = this.output.name;
            if (node.activeOutputs.exists(outputName)) {
                node.activeOutputs.remove(outputName);
                this.activeClass = false;
            } else {
                node.activeOutputs.add(outputName);
                this.activeClass = true;
            }
            manager.has_changes = true;
        },
    },
};
</script>
