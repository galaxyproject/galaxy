<template>
    <div class="form-row dataRow output-data-row">
        <div v-if="showCallout" :class="['callout-terminal', output.name]" @click="onToggle">
            <i :class="['mark-terminal', activeClass]" />
        </div>
        {{ label }}
        <div :id="id" :output-name="output.name" ref="terminal" :class="terminalClass">
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
    data() {
        return {
            isMultiple: false,
        };
    },
    computed: {
        id() {
            const node = this.getNode();
            return `node-${node.id}-output-${this.output.name}`;
        },
        label() {
            let extensions = this.output.extensions || this.output.type || "unspecified";
            if (Array.isArray(extensions)) {
                extensions = extensions.join(", ");
            }
            const activeLabel = this.output.activeLabel || this.output.label || this.output.name;
            return `${activeLabel} (${extensions})`;
        },
        activeClass() {
            return this.output.activeOutput && "mark-terminal-active";
        },
        showCallout() {
            const node = this.getNode();
            return node.type == "tool";
        },
        terminalClass() {
            const cls = "terminal output-terminal";
            if (this.isMultiple) {
                return `${cls} multiple`;
            }
            return cls;
        },
    },
    mounted() {
        const output = this.output;
        if (output.collection) {
            const collection_type = output.collection_type;
            const collection_type_source = output.collection_type_source;
            this.terminal = new Terminals.OutputCollectionTerminal({
                node: this.getNode(),
                name: output.name,
                element: this.$refs.terminal,
                collection_type: collection_type,
                collection_type_source: collection_type_source,
                datatypes: output.extensions,
                force_datatype: output.force_datatype,
                optional: output.optional,
            });
        } else if (output.parameter) {
            this.terminal = new Terminals.OutputParameterTerminal({
                node: this.getNode(),
                name: output.name,
                element: this.$refs.terminal,
                type: output.type,
                optional: output.optional,
            });
        } else {
            this.terminal = new Terminals.OutputTerminal({
                node: this.getNode(),
                name: output.name,
                element: this.$refs.terminal,
                datatypes: output.extensions,
                force_datatype: output.force_datatype,
                optional: output.optional,
            });
        }
        this.terminal.on("change", this.onChange.bind(this));
        new OutputDragging(this.getManager(), {
            el: this.$refs.terminal,
            terminal: this.terminal,
        });
        this.$emit("onAdd", this.output, this.terminal);
    },
    methods: {
        onChange() {
            this.isMultiple = this.terminal.mapOver && this.terminal.mapOver.isCollection;
            this.$emit("onChange");
        },
        onToggle() {
            this.$emit("onToggle", this.output.name);
        },
    },
};
</script>
