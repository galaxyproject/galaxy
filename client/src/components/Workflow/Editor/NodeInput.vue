<template>
    <div class="form-row dataRow input-data-row" @mouseover="mouseOver" @mouseleave="mouseLeave">
        <div :id="id" :input-name="input.name" :class="terminalClass" @drop="onDrop">
            <div ref="terminal" class="icon" />
        </div>
        <div v-if="showRemove" class="delete-terminal" @click="onRemove" />
        {{ label }}
    </div>
</template>

<script>
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
        rootOffset: {
            type: Object,
            required: true,
        },
        offsetX: {
            type: Number,
            required: true,
        },
        offsetY: {
            type: Number,
            required: true,
        },
    },
    data() {
        return {
            showRemove: false,
            isMultiple: false,
            initX: 0,
            initY: 0,
            nodeId: null,
        };
    },
    created() {
        this.nodeId = this.getNode().id;
    },
    mounted() {
        const rect = this.$refs.terminal.getBoundingClientRect();
        this.initX = rect.left + rect.width / 2 - this.rootOffset.left;
        this.initY = rect.top + rect.height / 2 - this.rootOffset.top;
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
        startX() {
            return this.initX + this.offsetX;
        },
        startY() {
            return this.initY + this.offsetY;
        },
        position() {
            return Object.freeze({ endX: this.startX, endY: this.startY });
        },
    },
    beforeDestroy() {
        this.$emit("onRemove", this.input);
        this.onRemove();
    },
    watch: {
        position(position) {
            console.log({
                stepId: this.nodeId,
                inputName: this.input.name,
                position,
            });
            this.$store.commit("workflowState/setInputTerminalPosition", {
                stepId: this.nodeId,
                inputName: this.input.name,
                position,
            });
        },
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
