<template>
    <div ref="overview" class="workflow-overview" :style="style" aria-hidden="true">
        <div class="workflow-overview-body">
            <svg width="100%" height="100%" :viewBox="viewBox">
                <MinimapNode
                    class="mini-node"
                    :node="node"
                    :step="steps[node.id]"
                    v-for="node of Object.values(nodes)"
                    :key="node.id" />
                <rect
                    class="mini-node"
                    :x="visible.x"
                    :y="visible.y"
                    :width="visible.width"
                    :height="visible.height"
                    fill-opacity="0.5" />
            </svg>
        </div>
    </div>
</template>
<script>
import MinimapNode from "./MinimapNode.vue";
import Draggable from "./Draggable.vue";
import { reactive, ref } from "vue";
import { useDraggable } from "@vueuse/core";

export default {
    setup() {
        const overview = ref(null);
        const overviewPosition = reactive(useDraggable(overview, { preventDefault: true }));
        return { overview, overviewPosition };
    },
    components: {
        Draggable,
        MinimapNode,
    },
    data() {
        return {
            size: 150,
            maxSize: 300,
            minSize: 50,
        };
    },
    props: {
        nodes: {
            type: Object,
            required: true,
        },
        steps: {
            type: Object,
            required: true,
        },
        width: {
            type: Number,
            default: 200,
        },
        height: {
            type: Number,
            default: 200,
        },
        scale: {
            type: Number,
            default: 1,
        },
        pan: {
            type: Object,
            default() {
                return { x: 0, y: 0 };
            },
        },
        rootOffset: {
            type: Object,
        },
    },
    computed: {
        style() {
            if (this.overviewPosition.x) {
                let newSize = Math.max(
                    this.rootOffset.right - this.overviewPosition.x,
                    this.rootOffset.bottom - this.overviewPosition.y
                );
                if (newSize > this.maxSize) {
                    newSize = this.maxSize;
                } else if (newSize < this.minSize) {
                    newSize = this.minSize;
                }
                this.size = newSize;
            }
            return { width: `${this.size}px`, height: `${this.size}px` };
        },
        visible() {
            // translate current rootOffset rectangle into scaled and panned space
            const x = this.pan.x / -this.scale;
            const y = this.pan.y / -this.scale;
            const width = this.rootOffset.width / this.scale;
            const height = this.rootOffset.bottom / this.scale;
            const rval = { x, y, width, height };
            return rval;
        },
        bounds() {
            let left = this.pan.x * -1;
            let right = this.rootOffset.width;
            let top = this.pan.y * -1;
            let bottom = this.rootOffset.bottom;
            let p;
            Object.values(this.steps).forEach((step) => {
                const node = this.nodes[step.id];
                p = node.position;
                left = Math.min(left, step.position.left);
                right = Math.max(right, p.right);
                top = Math.min(top, step.position.top);
                bottom = Math.max(bottom, p.bottom);
            });

            return {
                left: left / this.scale,
                right: right / this.scale,
                top: top / this.scale,
                bottom: bottom / this.scale,
            };
        },
        viewBox() {
            return `${this.bounds.left} ${this.bounds.top} ${this.bounds.right} ${this.bounds.bottom}`;
        },
    },
};
</script>
