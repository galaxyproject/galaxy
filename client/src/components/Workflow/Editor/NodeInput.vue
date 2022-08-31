<template>
    <div class="form-row dataRow input-data-row" @mouseover="mouseOver" @mouseleave="mouseLeave">
        <div :id="id" :input-name="input.name" :class="terminalClass" @drop="onDrop">
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
    beforeDestroy() {
        this.$emit("onRemove", this.input);
        this.onRemove();
    },
    methods: {
        onChange() {
            this.isMultiple = this.terminal.isMappedOver();
            this.$emit("onChange");
        },
        onRemove() {
            this.$emit("onDisconnect", this.input.name);
        },
        mouseOver(e) {
            console.log("mousOver");
            // if (this.terminal.connectors.length > 0) {
            //     this.showRemove = true;
            // }
        },
        mouseLeave() {
            this.showRemove = false;
        },
        onDrop(e) {
            console.log("onDrop", e);
        },
    },
};
</script>
