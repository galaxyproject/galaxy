<template>
    <draggable
        :draggable-options="draggableOptions"
        @start="onDragStart"
        @move="move"
        :stop="onStopDragging"
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
    },
    data() {
        return {
            mouseDown: {},
        };
    },
    computed: {
        draggableOptions() {
            return {
                mouseDown: this.stopPropagation,
            };
        },
    },
    methods: {
        onDragStart(e) {
            console.log("mousedown", e);
            this.$emit("mousedown", e);
        },
        onStopDragging(e) {
            console.log("stopDragging");
            e.stopPropagation();
            this.$emit("stopDragging");
            this.$emit("mouseup");
        },
        stopPropagation(e) {
            e.stopPropagation();
        },
        move(e) {
            console.log("moveEvent", e);
            e.event.stopPropagation();
        },
    },
};
</script>
