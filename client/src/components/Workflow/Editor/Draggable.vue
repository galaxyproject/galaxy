<!-- TODO: implement pan when dragged object leaves viewport -->
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
        scale() {
            return this.$store.getters["workflowState/getScale"]();
        },
        draggableOptions() {
            return {
                mouseDown: this.stopPropagation,
            };
        },
    },
    methods: {
        onDragStart(e) {
            this.$emit("mousedown", e);
        },
        onStopDragging(e) {
            e.stopPropagation();
            this.$emit("stopDragging");
            this.$emit("mouseup");
        },
        stopPropagation(e) {
            e.stopPropagation();
        },
        move(e) {
            // supposedly draggable can apply the scale if passed in the draggable-option prop,
            // but it doesn't, so we do it manually here.
            e.data.deltaX /= this.scale;
            e.data.deltaY /= this.scale;
            e.event.stopPropagation();
        },
    },
};
</script>
