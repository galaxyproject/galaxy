<template>
    <div
        ref="drag"
        draggable="true"
        @drag.stop="onDrag"
        @dragend.stop="onDragEnd"
        @mousedown.stop="onMouseDown"
        @click="$emit('click')">
        <slot></slot>
    </div>
</template>

<script>
export default {
    props: {
        position: {
            type: Object,
            required: false,
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
            _localPosition: {},
        };
    },
    computed: {
        localPosition() {
            if (this.position) {
                return this.position;
            } else {
                return this._localPosition;
            }
        },
    },
    methods: {
        onMouseDown(e) {
            this.mouseDown = { offsetX: e.offsetX, offsetY: e.offsetY };
            if (!this.position) {
                const { top, left } = this.$refs.drag.getBoundingClientRect();
                this._localPosition = { top: top + window.scrollY, left: left + window.scrollX };
            }
        },
        onDrag(e) {
            const left = this.localPosition.left + (e.offsetX - this.mouseDown.offsetX) / this.zoom;
            const top = this.localPosition.top + (e.offsetY - this.mouseDown.offsetY) / this.zoom;
            this.$emit("updatePosition", { left, top });
        },
        onDragEnd(e) {
            // this.onDrag(e);
            this.$emit("dragEnd");
        },
    },
};
</script>
