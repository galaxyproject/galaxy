<template>
    <div draggable="true" @drag="onDrag" @dragend="onDragEnd" @mousedown="onMouseDown" @click="$emit('click')">
        <slot></slot>
    </div>
</template>

<script>
export default {
    props: {
        position: {
            top: {
                type: Number,
                default: 0,
            },
            left: {
                type: Number,
                default: 0,
            },
        },
        zoom: {
            type: Number,
            default: 1,
            required: false,
        },
    },
    data() {
        return {
            mouseDown: {},
        };
    },
    methods: {
        onMouseDown(e) {
            this.mouseDown = { offsetX: e.offsetX, offsetY: e.offsetY };
        },
        onDrag(e) {
            const left = this.position.left + (e.offsetX - this.mouseDown.offsetX) / this.zoom;
            const top = this.position.top + (e.offsetY - this.mouseDown.offsetY) / this.zoom;
            this.$emit("updatePosition", { left, top });
        },
        onDragEnd(e) {
            // this.onDrag(e);
            this.$emit("dragEnd");
        },
    },
};
</script>
