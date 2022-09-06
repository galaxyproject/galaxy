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
        applyScale: {
            type: Boolean,
            required: false,
            default: true,
        },
    },
    data() {
        return {
            isPanning: false,
            // Maximum distance to move per pan
            maxDeltaPerPan: 8,
            // 60hz seems pretty common, should result in smooth panning
            refreshRate: 1000 / 60,
            panBy: {},
            timeout: null,
            programmaticDelta: { x: 0, y: 0 },
        };
    },
    computed: {
        scale() {
            if (this.applyScale) {
                return this.$store.getters["workflowState/getScale"]();
            }
            return 1;
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
                if (doMove) {
                    // we need to move in the opposite direction of the pan
                    const data = {
                        deltaX: (this.panBy.x / this.scale) * -1,
                        deltaY: (this.panBy.y / this.scale) * -1,
                    };
                    this.$emit("move", { event: {}, data });
                    this.programmaticDelta.x -= this.panBy.x;
                    this.programmaticDelta.y -= this.panBy.y;
                }
                this.timeout = setTimeout(() => {
                    this.emitPan();
                }, this.refreshRate);
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
                // Limit pan to maxDeltaPerPan
                const deltaX = Math.min(Math.abs(e.data.deltaX), this.maxDeltaPerPan);
                const deltaY = Math.min(Math.abs(e.data.deltaY), this.maxDeltaPerPan);
                // Check if we're out of bounds
                let doPan = false;
                const panBy = { x: 0, y: 0 };
                if (e.event.clientX - this.rootOffset.left < 0) {
                    panBy["x"] = deltaX;
                    doPan = true;
                }
                if (e.event.clientY - this.rootOffset.top < 0) {
                    panBy["y"] = deltaY;
                    doPan = true;
                }
                if (this.rootOffset.right - e.event.clientX < 0) {
                    panBy["x"] = -deltaX;
                    doPan = true;
                }
                if (this.rootOffset.bottom - e.event.clientY < 0) {
                    panBy["y"] = -deltaY;
                    doPan = true;
                }
                this.panBy = panBy;
                this.isPanning = doPan;
                this.emitPan(false);
            }
            // if we have moved the panel programmatically we need to "fix" the delta
            e.data.deltaX -= this.programmaticDelta.x;
            e.data.deltaY -= this.programmaticDelta.y;
            this.programmaticDelta = { x: 0, y: 0 };
            // supposedly draggable can apply the scale if passed in the draggable-option prop,
            // but it doesn't, so we do it manually here.
            e.data.deltaX /= this.scale;
            e.data.deltaY /= this.scale;
            e.event.stopPropagation();
        },
    },
    beforeDestroy() {
        clearTimeout(this.timeout);
    },
};
</script>
