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
                mouseDown: this.stopPropagation,
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
        onDragStart(e) {
            console.log("mousedown", e);
            this.$emit("mousedown", e);
        },
        onStopDragging(e) {
            console.log("stopDragging");
            e.stopPropagation();
            this.$emit("stopDragging");
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
