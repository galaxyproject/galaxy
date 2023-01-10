<template>
    <Draggable
        :root-offset="rootOffset"
        :prevent-default="preventDefault"
        :stop-propagation="stopPropagation"
        :drag-data="dragData"
        @move="onMove"
        @mouseup="onMouseUp"
        v-on="$listeners">
        <slot></slot>
    </Draggable>
</template>

<script>
import Draggable from "./Draggable.vue";

export default {
    components: {
        Draggable,
    },
    props: {
        rootOffset: {
            type: Object,
            required: true,
        },
        scale: {
            type: Number,
            required: false,
            default: 1,
        },
        preventDefault: {
            type: Boolean,
            default: true,
        },
        stopPropagation: {
            type: Boolean,
            default: true,
        },
        dragData: {
            type: Object,
            required: false,
            default: null,
        },
    },
    data() {
        return {
            isPanning: false,
            // distance to move per pan
            deltaPerPan: 8,
            // 60hz seems pretty common, should result in smooth panning
            refreshRate: 1000 / 60,
            panBy: {},
            timeout: null,
        };
    },
    beforeDestroy() {
        clearTimeout(this.timeout);
    },
    methods: {
        emitPan(position) {
            if (this.isPanning) {
                this.$emit("pan-by", this.panBy);
                // we need to move in the opposite direction of the pan
                position.x -= this.panBy.x;
                position.y -= this.panBy.y;
                this.$emit("move", position);
            }
            this.timeout = setTimeout(() => {
                this.emitPan(position);
            }, this.refreshRate);
        },
        onMove(position, event) {
            clearTimeout(this.timeout);
            // Check if we're out of bounds
            let doPan = false;
            const panBy = { x: 0, y: 0 };
            const delta = this.deltaPerPan / this.scale;
            if (position.unscaled.x - this.rootOffset.left < 0) {
                panBy["x"] = delta;
                doPan = true;
            }
            if (position.unscaled.y - this.rootOffset.top < 0) {
                panBy["y"] = delta;
                doPan = true;
            }
            if (this.rootOffset.right - position.unscaled.x - position.unscaled.width * this.scale < 0) {
                panBy["x"] = -delta;
                doPan = true;
            }
            if (this.rootOffset.bottom - position.unscaled.y - position.unscaled.height * this.scale < 0) {
                panBy["y"] = -delta;
                doPan = true;
            }
            this.$emit("move", position, event);
            this.panBy = panBy;
            this.isPanning = doPan;
            this.emitPan(position);
        },
        onMouseUp(e) {
            this.isPanning = false;
            this.$emit("mouseup", e);
        },
    },
};
</script>
