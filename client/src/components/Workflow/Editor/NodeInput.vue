<template>
    <div class="form-row dataRow input-data-row" @mouseover="mouseOver" @mouseleave="mouseLeave">
        <div :id="id" ref="terminal" :input-name="input.name" :class="terminalClass">
            <div class="icon" />
        </div>
        <div v-if="showRemove" class="delete-terminal" @click="onRemove" />
        {{ label }}
    </div>
</template>

<script>
import Terminals from "./modules/terminals";
import { InputDragging } from "./modules/dragging";
import Connector from "./modules/connector";
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
        datatypesMapper: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {
            showRemove: false,
            isMultiple: false,
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
        terminalClass() {
            const cls = "terminal input-terminal";
            if (this.isMultiple) {
                return `${cls} multiple`;
            }
            return cls;
        },
    },
    watch: {
        input: function (newInput) {
            const oldTerminal = this.terminal;
            if (oldTerminal instanceof this.terminalClassForInput(newInput)) {
                oldTerminal.update(newInput);
                oldTerminal.destroyInvalidConnections();
            } else {
                // create new terminal, connect like old terminal, destroy old terminal
                this.$emit("onRemove", this.input);
                const newTerminal = this.createTerminal(newInput);
                newTerminal.connectors = this.terminal.connectors.map((c) => {
                    return new Connector(this.getManager(), c.outputHandle, newTerminal);
                });
                newTerminal.destroyInvalidConnections();
                this.terminal = newTerminal;
                oldTerminal.destroy();
            }
        },
    },
    mounted() {
        this.terminal = this.createTerminal(this.input);
    },
    beforeDestroy() {
        this.$emit("onRemove", this.input);
        this.onRemove();
    },
    methods: {
        terminalClassForInput(input) {
            let terminalClass = Terminals.InputTerminal;
            if (input.input_type == "dataset_collection") {
                terminalClass = Terminals.InputCollectionTerminal;
            } else if (input.input_type == "parameter") {
                terminalClass = Terminals.InputParameterTerminal;
            }
            return terminalClass;
        },
        createTerminal(input) {
            const terminalClass = this.terminalClassForInput(input);
            const terminal = new terminalClass({
                node: this.getNode(),
                datatypesMapper: this.datatypesMapper,
                name: input.name,
                input: input,
                element: this.$refs.terminal,
            });
            terminal.on("change", this.onChange.bind(this));
            new InputDragging(this.getManager(), {
                el: this.$refs.terminal,
                terminal: terminal,
            });
            this.$emit("onAdd", this.input, terminal);
            return terminal;
        },
        onChange() {
            this.isMultiple = this.terminal.isMappedOver();
            this.$emit("onChange");
        },
        onRemove() {
            this.terminal.destroy();
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
