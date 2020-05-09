<template>
    <div class="form-row dataRow output-data-row">
        <div v-if="showCallout" :class="['callout-terminal', output.name]" @click="onToggle">
            <i :class="['mark-terminal', activeClass]" />
        </div>
        {{ label }}
        <div :id="id" :output-name="output.name" ref="terminal" class="terminal output-terminal">
            <div class="icon" />
        </div>
    </div>
</template>

<script>
import Terminals from "./modules/terminals";
import { OutputDragging } from "./modules/dragging";

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
    computed: {
        id() {
            const node = this.getNode();
            return `node-${node.id}-output-${this.output.name}`;
        },
        label() {
            return this.output.labelActive || this.output.name;
        },
        activeClass() {
            return this.output.isActiveOutput && "mark-terminal-active";
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
        new OutputDragging(this.getManager(), {
            node: this.getNode(),
            output: output,
            el: this.$refs.terminal,
            terminal: this.terminal,
        });
        this.$emit("onAdd", this.output, this.terminal);
    },
    methods: {
        onToggle() {
            this.$emit("onToggle", this.output.name);
        },
    },
};
</script>
