<template>
    <div class="form-row dataRow input-data-row" @mouseover="mouseOver" @mouseleave="mouseLeave">
        <div :id="id" :input-name="input.name" ref="terminal" :class="terminalClass">
            <div class="icon" />
        </div>
        <div v-if="showRemove" class="delete-terminal" @click="onRemove" />
        {{ label }}
    </div>
</template>

<script>
import Terminals from "./modules/terminals";
import { InputDragging } from "./modules/dragging";
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
            const terminal = new terminalClass({
                app: this.getManager(),
                node: this.getNode(),
                name: input.name,
                input: input,
                element: this.$refs.terminal,
            });
            terminal.on("change", this.onChange.bind(this));
            new InputDragging(this.getManager(), {
                el: this.$refs.terminal,
                terminal: terminal,
            });
            return terminal;
        },
        onChange() {
            this.isMultiple = this.terminal.mapOver && this.terminal.mapOver.isCollection;
            this.$emit("onChange");
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
