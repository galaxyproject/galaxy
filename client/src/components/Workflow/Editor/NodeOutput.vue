<template>
    <div class="form-row dataRow output-data-row">
        <div
            v-if="showCallout"
            :class="['callout-terminal', output.name]"
            @click="onToggle"
            v-b-tooltip
            title="Unchecked outputs will be hidden and are not available as subworkflow outputs."
        >
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
import Connector from "./modules/connector";

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
            const activeLabel = this.activeOutput?.activeLabel || this.output.label || this.output.name;
            return `${activeLabel} (${extensions})`;
        },
        activeOutput() {
            return this.getNode().activeOutputs.outputsIndex[this.output.name];
        },
        activeClass() {
            return this.activeOutput?.activeOutput && "mark-terminal-active";
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
    watch: {
        output: function (newOutput) {
            const oldTerminal = this.terminal;
            if (oldTerminal instanceof this.terminalClassForOutput(newOutput)) {
                oldTerminal.update(newOutput);
                oldTerminal.destroyInvalidConnections();
            } else {
                // create new terminal, connect like old terminal, destroy old terminal
                this.$emit("onRemove", this.output);
                const newTerminal = this.createTerminal(newOutput);
                newTerminal.connectors = this.terminal.connectors.map((c) => {
                    return new Connector(this.getManager(), newTerminal, c.inputHandle);
                });
                newTerminal.destroyInvalidConnections();
                this.terminal = newTerminal;
                oldTerminal.destroy();
            }
        },
    },
    mounted() {
        this.terminal = this.createTerminal(this.output);
    },
    methods: {
        terminalClassForOutput(output) {
            let terminalClass = Terminals.OutputTerminal;
            if (output.collection) {
                terminalClass = Terminals.OutputCollectionTerminal;
            } else if (output.parameter) {
                terminalClass = Terminals.OutputParameterTerminal;
            }
            return terminalClass;
        },
        createTerminal(output) {
            let terminal;
            const terminalClass = this.terminalClassForOutput(output);
            const parameters = {
                node: this.getNode(),
                name: output.name,
                element: this.$refs.terminal,
                optional: output.optional,
            };
            if (output.collection) {
                const collection_type = output.collection_type;
                const collection_type_source = output.collection_type_source;
                terminal = new terminalClass({
                    ...parameters,
                    collection_type: collection_type,
                    collection_type_source: collection_type_source,
                    datatypes: output.extensions,
                });
            } else if (output.parameter) {
                terminal = new terminalClass({
                    ...parameters,
                    type: output.type,
                });
            } else {
                terminal = new terminalClass({
                    ...parameters,
                    datatypes: output.extensions,
                });
            }
            terminal.on("change", this.onChange.bind(this));
            new OutputDragging(this.getManager(), {
                el: this.$refs.terminal,
                terminal: terminal,
            });
            this.$emit("onAdd", this.output, terminal);
            return terminal;
        },
        onChange() {
            this.isMultiple = this.terminal.mapOver && this.terminal.mapOver.isCollection;
            this.$emit("onChange");
        },
        onToggle() {
            this.$emit("onToggle", this.output.name);
        },
    },
    beforeDestroy() {
        this.$emit("onRemove", this.output);
        this.terminal.destroy();
    },
};
</script>
