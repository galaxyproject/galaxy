<template>
    <draggable
        :draggable-options="draggableOptions"
        @move="move"
        :stop="stopPropagation"
        :start="stopPropagation"
        :drag="stopPropagation"
        v-on="$listeners">
        <slot></slot>
    </draggable>
</template>

<script>
import { Draggable } from "@braks/revue-draggable";

export default {
    components: {
        Draggable,
    },
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
        draggableOptions() {
            return {
                defaultPosition: null,
            };
        },
        localPosition() {
            if (this.position) {
                return this.position;
            } else {
                return this._localPosition;
            }
        },
    },
    methods: {
        stopPropagation(e) {
            e.stopPropagation();
        },
        move(e) {
            console.log("moveEvent", e);
            e.event.stopPropagation();
        },
        // onMouseDown(e) {
        //     this.mouseDown = { offsetX: e.offsetX, offsetY: e.offsetY };
        //     if (!this.position) {
        //         const { top, left } = this.$refs.drag.getBoundingClientRect();
        //         this._localPosition = { top: top + window.scrollY, left: left + window.scrollX };
        //     }
        // },
        // onDrag(e) {
        //     const left = this.localPosition.left + (e.offsetX - this.mouseDown.offsetX) / this.zoom;
        //     const top = this.localPosition.top + (e.offsetY - this.mouseDown.offsetY) / this.zoom;
        //     this.$emit("updatePosition", { left, top });
        // },
        // onDragEnd(e) {
        //     // this.onDrag(e);
        //     this.$emit("dragEnd");
        // },
    },
};
</script>
