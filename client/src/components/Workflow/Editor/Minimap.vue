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
                    class="viewport"
                    ref="rect"
                    :x="visible.x"
                    :y="visible.y"
                    :width="visible.width"
                    :height="visible.height"
                    stroke-width="1%"
                    rx="1%"
                    fill="white"
                    fill-opacity="0.5" />
            </svg>
        </div>
    </div>
</template>
<script>
import MinimapNode from "./MinimapNode.vue";
import Draggable from "./Draggable.vue";
import { computed, reactive, ref, watchEffect } from "vue";
import { useDraggable } from "@vueuse/core";

export default {
    setup(props, { emit }) {
        const overview = ref(null);
        const overviewPosition = reactive(useDraggable(overview, { preventDefault: true, exact: true }));
        const size = ref(parseInt(localStorage.getItem("overview-size")) || 150);
        const visible = computed(() => {
            const x = props.pan.x / -props.scale;
            const y = props.pan.y / -props.scale;
            const width = props.rootOffset.width / props.scale;
            const height = props.rootOffset.bottom / props.scale;
            const rval = { x, y, width, height };
            return rval;
        });
        const bounds = computed(() => {
            let left = props.pan.x * -1;
            let right = props.rootOffset.width;
            let top = props.pan.y * -1;
            let bottom = props.rootOffset.bottom;
            let p;
            Object.values(props.steps).forEach((step) => {
                const node = props.nodes[step.id];
                p = node.position;
                left = Math.min(left, step.position.left);
                right = Math.max(right, p.right);
                top = Math.min(top, step.position.top);
                bottom = Math.max(bottom, p.bottom);
            });

            return {
                left: left / props.scale,
                right: right / props.scale,
                top: top / props.scale,
                bottom: bottom / props.scale,
            };
        });
        const scaleFactorX = computed(() => {
            return (bounds.value.right - bounds.value.left) / size.value;
        });
        const scaleFactorY = computed(() => {
            return (bounds.value.bottom - bounds.value.top) / size.value;
        });
        const rect = ref(null);
        let startX = null;
        let startY = null;
        const rectPosition = reactive(
            useDraggable(rect, {
                preventDefault: true,
                onStart: (position, event) => {
                    event.stopPropagation();
                    startX = event.clientX;
                    startY = event.clientY;
                },
                onMove: (position, event) => {
                    const offsetX = event.clientX - startX;
                    const offsetY = event.clientY - startY;
                    console.log("panX", props.pan.x - offsetX * scaleFactorX.value);
                    console.log("panY", props.pan.y - offsetY * scaleFactorY.value);
                    emit("pan-by", { x: -offsetX * scaleFactorX.value, y: -offsetY * scaleFactorY.value });
                    startX = event.clientX;
                    startY = event.clientY;
                },
                // onEnd: (position, event) => {
                //     startX = null;
                //     startY = null;
                // },
            })
        );
        return {
            overview,
            overviewPosition,
            rect,
            rectPosition,
            size,
            visible,
            bounds,
            scaleFactorX,
            scaleFactorY,
            startX,
            startY,
        };
    },
    components: {
        Draggable,
        MinimapNode,
    },
    data() {
        return {
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
                if (!this.overviewPosition.isDragging) {
                    localStorage.setItem("overview-size", newSize);
                }
                this.size = newSize;
            }
            return { width: `${this.size}px`, height: `${this.size}px` };
        },
        viewBox() {
            return `${this.bounds.left} ${this.bounds.top} ${this.bounds.right} ${this.bounds.bottom}`;
        },
    },
    methods: {
        onClick(e) {
            console.log("panX", this.pan.x - offsetX * this.scaleFactorX);
            console.log("panY", this.pan.y - offsetY * this.scaleFactorY);
            // console.log("got click", e);
            // const scaledOffsetX = e.offsetX * this.scaleFactorX;
            // const scaledOffsetY = e.offsetY * this.scaleFactorY;
            // console.log("scaled offset", scaledOffsetX, scaledOffsetY);
            // const x = scaledOffsetX - this.rootOffset.width / 2;
            // const y = scaledOffsetY - this.rootOffset.height / 2;
            // console.log("adjusted offset", x, y);
            console.log("panX", props.pan.x - offsetX * scaleFactorX.value);
            this.$emit("moveTo", { x: -x, y: -y });
        },
    },
};
</script>
