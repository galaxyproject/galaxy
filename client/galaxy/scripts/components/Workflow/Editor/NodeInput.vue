<template>
    <div class="form-row dataRow input-data-row" @mouseover="mouseOver" @mouseleave="mouseLeave">
        <div ref="terminal" class="terminal input-terminal" />
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
            required: true
        },
        getManager: {
            type: Function,
            required: true
        },
    },
    data() {
        return {
            showRemove: false,
        };
    },
    computed: {
        label() {
            return this.input.label || this.input.name;
        },
    },
    mounted() {
        var terminalClass = Terminals.InputTerminal;
        const input = this.input;
        if (input.input_type == "dataset_collection") {
            terminalClass = Terminals.InputCollectionTerminal;
        } else if (input.input_type == "parameter") {
            terminalClass = Terminals.InputParameterTerminal;
        }
        if (this.terminal && !(this.terminal instanceof terminalClass)) {
            this.terminal.destroy();
        }
        this.terminal = new terminalClass({
            app: this.getManager(),
            element: this.$refs.terminal,
            input: input,
        });
        this.$emit("onAdd", this.input, this.terminal);
        new TerminalViews.InputTerminalView(this.getManager(), {
            node: this.getNode(),
            input: this.input,
            el: this.$refs.terminal,
            terminal: this.terminal,
        });
    },
    methods: {
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
