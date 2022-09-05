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
        rootOffset: {
            type: Object,
            required: false,
        },
    },
    data() {
        return {
            mouseDown: {},
            isPanning: false,
            nudge: 23,
            panBy: {},
            timeout: null,
            lastEvent: null,
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
        emitPan(doMove = true) {
            if (this.isPanning) {
                this.$emit("pan-by", this.panBy);
                // we need to move in the opposite direction of the pan
                const data = {
                    ...this.lastEvent.data,
                    deltaX: (this.panBy.x / this.scale) * -1,
                    deltaY: (this.panBy.y / this.scale) * -1,
                };
                console.log("move data", data);
                if (doMove) {
                    this.$emit("move", { ...this.lastEvent, data });
                }
                this.timeout = setTimeout(() => {
                    this.emitPan();
                }, 500);
            }
        },
        onDragStart(e) {
            this.$emit("mousedown", e);
        },
        onStopDragging(e) {
            this.isPanning = false;
            clearTimeout(this.timeout);
            e.stopPropagation();
            this.$emit("stopDragging");
            this.$emit("mouseup");
        },
        stopPropagation(e) {
            e.stopPropagation();
        },
        move(e) {
            clearTimeout(this.timeout);
            if (this.rootOffset) {
                const panBy = { x: 0, y: 0 };
                let doPan = false;
                if (e.event.clientX - this.rootOffset.left < 0) {
                    // panBy["x"] = Math.min(this.nudge, this.rootOffset.left - e.event.clientX);
                    panBy["x"] = this.rootOffset.left - e.event.clientX;
                    doPan = true;
                }
                if (e.event.clientY - this.rootOffset.top < 0) {
                    // panBy["y"] = Math.min(this.nudge, this.rootOffset.top - e.event.clientY);
                    panBy["y"] = this.rootOffset.top - e.event.clientY;
                    doPan = true;
                }
                if (this.rootOffset.right - e.event.clientX < 0) {
                    // panBy["x"] = Math.max(-this.nudge, this.rootOffset.right - e.event.clientX);
                    doPan = true;
                }
                if (this.rootOffset.bottom - e.event.clientY < 0) {
                    // panBy["y"] = Math.max(-this.nudge, this.rootOffset.bottom - e.event.clientY);
                    doPan = true;
                }
                this.panBy = panBy;
                this.isPanning = doPan;
                this.lastEvent = e;
                this.emitPan();
            }
            // supposedly draggable can apply the scale if passed in the draggable-option prop,
            // but it doesn't, so we do it manually here.
            e.data.deltaX /= this.scale;
            e.data.deltaY /= this.scale;
            e.event.stopPropagation();
        },
    },
};
</script>
