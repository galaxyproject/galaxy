<template>
    <div class="form-row dataRow input-data-row" @mouseover="mouseOver" @mouseleave="mouseLeave">
        <div :id="id" :input-name="input.name" ref="terminal" class="terminal input-terminal" />
        <div v-if="showRemove" class="delete-terminal" @click="onRemove" />
        {{ label }}
    </div>
</template>

<script>
import Terminals from "mvc/workflow/workflow-terminals";
import TerminalViews from "mvc/workflow/workflow-view-terminals";
export default {
    props: {
        input: {
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
            showRemove: false,
        };
    },
    computed: {
        id() {
            const node = this.getNode();
            return `node-${node.id}-input-${this.input.name}`;
        },
        label() {
            return this.input.label || this.input.name;
        },
    },
    mounted() {
        this.terminal = this.createTerminal(this.input);
        this.$emit("onAdd", this.input, this.terminal);
    },
    methods: {
        createTerminal(input) {
            let terminalClass = Terminals.InputTerminal;
            if (input.input_type == "dataset_collection") {
                terminalClass = Terminals.InputCollectionTerminal;
            } else if (input.input_type == "parameter") {
                terminalClass = Terminals.InputParameterTerminal;
            }
            if (this.terminal && !(this.terminal instanceof terminalClass)) {
                this.terminal.destroy();
            }
            const terminal = new terminalClass({
                app: this.getManager(),
                element: this.$refs.terminal,
                input: input,
            });
            new TerminalViews.InputTerminalView(this.getManager(), {
                node: this.getNode(),
                input: this.input,
                el: this.$refs.terminal,
                terminal: terminal,
            });
            return terminal;
        },
        onRemove() {
            this.$emit("onRemove");
            if (this.terminal.connectors.length > 0) {
                this.terminal.connectors.forEach((x) => {
                    if (x) {
                        x.destroy();
                    }
                });
            }
        },
        mouseOver(e) {
            if (this.terminal.connectors.length > 0) {
                this.showRemove = true;
            }
        },
        mouseLeave() {
            this.showRemove = false;
        },
    },
};
</script>
