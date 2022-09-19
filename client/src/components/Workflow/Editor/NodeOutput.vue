<template>
    <div class="form-row dataRow output-data-row">
        <div
            v-if="showCallout"
            v-b-tooltip
            :class="['callout-terminal', output.name]"
            title="Unchecked outputs will be hidden and are not available as subworkflow outputs."
            @click="onToggle">
            <i :class="['mark-terminal', activeClass]" />
        </div>
        {{ label }}
        <div :id="id" ref="terminal" :output-name="output.name" :class="terminalClass">
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
        postJobActions: {
            type: Object,
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
            const activeLabel = this.output.activeLabel || this.output.label || this.output.name;
            return `${activeLabel} (${this.extensions.join(", ")})`;
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
        forcedExtension() {
            const changeDatatype =
                this.postJobActions[`ChangeDatatypeAction${this.output.label}`] ||
                this.postJobActions[`ChangeDatatypeAction${this.output.name}`];
            return changeDatatype?.action_arguments.newtype;
        },
        extensions() {
            let extensions = this.forcedExtension || this.output.extensions || this.output.type || "unspecified";
            if (!Array.isArray(extensions)) {
                extensions = [extensions];
            }
            return extensions;
        },
        effectiveOutput() {
            return { ...this.output, extensions: this.extensions };
        },
    },
    watch: {
        label() {
            // See discussion at: https://github.com/vuejs/vue/issues/8030
            this.$nextTick(() => {
                this.$emit("onChange");
            });
        },
        effectiveOutput(newOutput) {
            const oldTerminal = this.terminal;
            if (oldTerminal instanceof this.terminalClassForOutput(newOutput)) {
                oldTerminal.update(newOutput);
                oldTerminal.destroyInvalidConnections();
            } else {
                // create new terminal, connect like old terminal, destroy old terminal
                // this might be a little buggy, we should replace this with proper vue components
                this.$emit("onRemove", this.output);
                this.createTerminal(newOutput);
                this.terminal.connectors = oldTerminal.connectors.map((c) => {
                    return new Connector(this.getManager().canvasManager, this.terminal, c.inputHandle);
                });
                this.terminal.destroyInvalidConnections();
                oldTerminal.destroy();
            }
        },
    },
    mounted() {
        this.createTerminal(this.output);
    },
    beforeDestroy() {
        this.$emit("onRemove", this.output);
        this.terminal.destroy();
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
                this.terminal = new terminalClass({
                    ...parameters,
                    collection_type: collection_type,
                    collection_type_source: collection_type_source,
                    datatypes: this.extensions,
                });
            } else if (output.parameter) {
                this.terminal = new terminalClass({
                    ...parameters,
                    type: output.type,
                });
            } else {
                this.terminal = new terminalClass({
                    ...parameters,
                    datatypes: this.extensions,
                });
            }
            new OutputDragging(this.getManager(), {
                el: this.$refs.terminal,
                terminal: this.terminal,
            });
            this.terminal.on("change", this.onChange.bind(this));
            this.terminal.emit("change");
            this.$emit("onAdd", this.output, this.terminal);
        },
        onChange() {
            this.isMultiple = this.terminal.isMappedOver();
            this.$emit("onChange");
        },
        onToggle() {
            this.$emit("onToggle", this.output.name);
        },
    },
};
</script>
