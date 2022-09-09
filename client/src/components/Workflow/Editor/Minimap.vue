<template>
    <div class="workflow-overview" aria-hidden="true">
        <div class="workflow-overview-body">
            <div id="overview-container">
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
                <div id="overview-viewport" />
            </div>
        </div>
    </div>
</template>
<script>
import MinimapNode from "./MinimapNode.vue";

export default {
    components: {
        MinimapNode,
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
